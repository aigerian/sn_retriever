import datetime

__author__ = '4ikist'

import base64
import json
import logging
import time

import requests
from properties import *
from contrib.api.entities import API, APIRequestOverflowException

user_info = [
    'id',
    'verified',
    'followers_count',
    'statuses_count',
    'description',
    'friends_count',
    'screen_name',
    'lang',
    'favourites_count',
    'name',
    'created_at', #use datetime
    'contributors_enabled',
    'protected',
    'default_profile',
    'status', #get created at and text
]


class TTR_API(API):
    @property
    def name(self):
        return 'ttr'

    @staticmethod
    def get_dt(input):
        return datetime.datetime.strptime(input, '%a %b %d %H:%M:%S +0000 %Y')

    def __init__(self):
        self.basic_url = 'https://api.twitter.com'
        self.log = logging.getLogger('TTR_API')
        token = None
        while not token:
            self.log.warn('trying to auth in twitter')
            token = self.__auth()
            if token:
                break
            time.sleep(10)
        self.bearer_token = token

    def __auth(self):
        s = requests.Session()
        s.verify = certs_path
        self.log.info('processing auth')
        issue_key = base64.standard_b64encode('%s:%s' % (ttr_consumer_key, ttr_consumer_secret))
        headers = {'User-Agent': 'ttr_retr',
                   'Authorization': 'Basic %s' % issue_key,
                   'Content-type': 'application/x-www-form-urlencoded;charset=UTF-8'}
        result = s.post('%s/oauth2/token' % self.basic_url,
                        headers=headers,
                        data='grant_type=client_credentials')
        self.log.debug('>> %s \nheaders:\t%s' % (result.request.url, result.request.headers))
        self.log.debug('<< [%s] %s' % (result.status_code, result.text))
        if result.status_code == 200:
            result_json = json.loads(result.content)
            bearer_token = result_json['access_token']
            self.log.info('bearer token: %s' % bearer_token)
            return bearer_token
        else:
            self.log.warn('can not auth :(')
            return None


    def get(self, command, dump_to=None, **kwargs):
        """
        :param command: - the command for twitter api rest
        :param dump_to:  - some object which have .write() method
        :param kwargs:  - command parameters
        :return: - python object of result twitter api or None
        :raise: APIOutException with errors description
        """
        headers = {'Authorization': 'Bearer %s' % self.bearer_token}
        result = requests.get('%s/1.1/%s.json' % (self.basic_url, command), headers=headers, params=kwargs)
        try:
            result = json.loads(result.content)
            if dump_to:
                json.dump(result, dump_to)
            if hasattr(result, 'errors'):
                raise APIRequestOverflowException('%s' % result['errors'])
            return result
        except ValueError as e:
            self.log.error('result have not contain json object')
            self.log.exception(e)

    def _get_all(self, command, **kwargs):
        all = []
        page = 1
        kwargs['page'] = page
        while True:
            try:
                result = self.get(command, **kwargs)
                if len(result):
                    kwargs['page'] += 1
                    all.extend(result)
                else:
                    break
            except APIRequestOverflowException as e:
                break
        return all

    def _get_cursored(self, cursored_first_result, list_name, command, **kwargs):
        """
        input cursored result
        :return: full result
        """
        full_list = cursored_first_result[list_name]
        cursor = cursored_first_result['next_cursor']
        self.log.debug('\ngetting cursored results:')
        iter_count = 0
        while True:
            if cursor == 0 or iter_count == cursor_iterations:
                break
            iter_count += 1
            cursor = cursored_first_result['next_cursor']
            kwargs['cursor'] = cursor

            try:
                batch_result = self.get(command, **kwargs)
            except APIRequestOverflowException as e:
                self.log.exception(e)
                self.log.warn('for this request i retrieve only %s %s' % (len(full_list), list_name))
                return cursored_first_result

            if batch_result and 'next_cursor' in batch_result and list_name in batch_result:
                full_list.extend(batch_result[list_name])
                cursor = batch_result['next_cursor']
            else:
                break
        self.log.info('full list count is %s %s' % (len(full_list), list_name))
        full_result = cursored_first_result
        full_result[list_name] = full_list
        return full_result


    def get_user(self, user_id=None, screen_name=None):
        """
        return user representation
        :param user_id:
        :param screen_name:
        :return:
            user information: [
            'id',
            'verified',
            'followers_count',
            'statuses_count',
            'description',
            'friends_count',
            'screen_name',
            'lang',
            'favourites_count',
            'name',
            'created_at [dt]',
            'contributors_enabled',
            'protected',
            'default_profile',
            'status - created_at',
            'status - text',
            ]
        """

        kwargs = {'user_id': user_id, 'screen_name': screen_name}
        command = "users/show"
        result = self.get(command, **kwargs)
        final_result = {}
        if result and isinstance(result, dict):
            for el in user_info:
                if el == 'status':
                    final_result[el + '_created_at'] = TTR_API.get_dt(result.get(el)['created_at'])
                    final_result[el + '_text'] = result.get(el)['text']
                elif el == 'created_at':
                    final_result[el] = TTR_API.get_dt(result.get(el))
                else:
                    final_result[el] = result.get(el)
        return final_result

    def get_user_timeline(self, user_id=None, screen_name=None):
        params = {'user_id': user_id, 'screen_name': screen_name, 'count': 200, 'include_rts': 1, 'trim_user': 1}
        command = "statuses/user_timeline"
        result = self._get_all(command, **params)
        return result

    def get_relations(self, user_id=None, screen_name=None, relation_type='friends'):
        """
        returning json object of user relations
        :param user_id:
        :param screen_name:
        :param relation_type: can be followers or friends
        :return:
        """
        kwargs = {'user_id': user_id, 'screen_name': screen_name, 'count': 5000, 'cursor': -1}
        command = '%s/ids' % relation_type

        first_result = self.get(command, **kwargs)
        full_result = self._get_cursored(first_result, 'ids', command, **kwargs)
        return full_result[u'ids']

    def search(self, q):
        params = {'count': 100, 'q': q}
        command = 'search/tweets'
        tweet_result = self.get(command, **params).get('statuses')
        return tweet_result
