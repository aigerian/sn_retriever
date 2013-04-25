#coding: utf-8
__author__ = '4ikist'

import json
import requests
import base64
import logging

from properties import *


log = logging.getLogger('API')


class ApiConnection(object):
    def __init__(self):
        self.basic_url = 'https://api.twitter.com'
        token = self.__auth()
        if token:
            self.bearer_token = token

    def __auth(self):
        log.info('processing auth')
        issue_key = base64.standard_b64encode('%s:%s' % (consumer_key, consumer_secret))
        headers = {'User-Agent': 'ttr_retr',
                   'Authorization': 'Basic %s' % issue_key,
                   'Content-type': 'application/x-www-form-urlencoded;charset=UTF-8'}
        result = requests.post('%s/oauth2/token' % self.basic_url,
                               headers=headers,
                               data='grant_type=client_credentials')
        log.debug('>> %s \nheaders:\t%s' % (result.request.url, result.request.headers))
        log.debug('<< [%s] %s' % (result.status_code, result.text))
        if result.status_code == 200:
            result_json = json.loads(result.content)
            bearer_token = result_json['access_token']
            log.info('bearer token: %s' % bearer_token)
            return bearer_token
        else:

            log.warn('can not auth :(')
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
                raise APIOutException('%s' % result['errors'])
            return result
        except ValueError as e:
            log.error('result have not contain json object')
            log.exception(e)

    def get_cursored(self, cursored_first_result, list_name, command, **kwargs):
        """
        input cursored result
        :return: full result
        """
        full_list = cursored_first_result[list_name]
        cursor = cursored_first_result['next_cursor']
        log.debug('\ngetting cursored results:')
        iter_count = 0
        while True:
            if cursor == 0 or iter_count == cursor_iterations:
                break
            iter_count += 1
            cursor = cursored_first_result['next_cursor']
            kwargs['cursor'] = cursor

            try:
                batch_result = self.get(command, **kwargs)
            except APIOutException as e:
                log.exception(e)
                log.warn('for this request i retrieve only %s %s' % (len(full_list), list_name))
                return cursored_first_result

            if batch_result and 'next_cursor' in batch_result and list_name in batch_result:
                full_list.extend(batch_result[list_name])
                cursor = batch_result['next_cursor']
            else:
                break
        log.info('full list count is %s %s' % (len(full_list), list_name))
        full_result = cursored_first_result
        full_result[list_name] = full_list
        return full_result

    def get_followers(self, user_id=None, screen_name=None):
        if not user_id and not screen_name:
            raise APIInException('specify user id or screen name')

        kwargs = {'user_id': user_id, 'screen_name': screen_name, 'count': 5000, 'cursor': -1}
        command = 'followers/ids'

        first_result = self.get(command, **kwargs)
        full_result = self.get_cursored(first_result, 'ids', command, **kwargs)
        return full_result


class APIOutException(Exception): pass


class APIInException(Exception): pass