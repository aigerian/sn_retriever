# coding=utf-8
import datetime
from properties import certs_path, vk_access_credentials, vk_login, vk_pass, vk_fields, logger
from contrib.api.entities import API, APIException, APIUser, APIMessage

import json
import re
import urlparse

from lxml import html
import requests

__author__ = '4ikist'

class VK_API(API):
    def __init__(self):
        self.log = logger.getChild('VK_API')
        self.access_token = self.__auth()
        self.base_url = 'https://api.vk.com/method/'
        self.array_item_process = lambda x: x[1:]
        self.array_count_process = lambda x: x[0]

    def __auth(self):
        """
        authenticate in vk with dirty hacks
        :return: access token
        """
        #process first page
        self.log.info('vkontakte authenticate')
        s = requests.Session()
        s.verify = certs_path
        result = s.get('https://oauth.vk.com/authorize', params=vk_access_credentials)
        doc = html.document_fromstring(result.content)
        inputs = doc.xpath('//input')
        form_params = {}
        for el in inputs:
            form_params[el.attrib.get('name')] = el.value
        form_params['email'] = vk_login
        form_params['pass'] = vk_pass
        form_url = doc.xpath('//form')[0].attrib.get('action')
        #process second page
        result = s.post(form_url, form_params)
        doc = html.document_fromstring(result.content)
        #if already login
        if 'OAuth Blank' not in doc.xpath('//title')[0].text:
            submit_url = doc.xpath('//form')[0].attrib.get('action')
            result = s.post(submit_url, cookies=result.cookies)

        #retrieving access token from url
        parsed_url = urlparse.urlparse(result.url)
        if 'error' in parsed_url.query:
            self.log.error('error in authenticate \n%s' % parsed_url.query)
            raise APIException(dict([el.split('=') for el in parsed_url.query.split('&')]))

        fragment = parsed_url.fragment
        access_token = dict([el.split('=') for el in fragment.split('&')])
        self.log.info('get access token: \n%s' % access_token)
        return access_token

    def get(self, method_name, **kwargs):
        params = dict({'access_token': self.access_token['access_token']}, **kwargs)
        result = requests.get('%s%s' % (self.base_url, method_name), params=params)
        result_object = json.loads(result.content)
        if 'error' in result_object:
            raise APIException(result_object)
        return result_object['response']

    def get_all(self, method_name, batch_size=200, items_process=lambda x: x['items'],
                count_process=lambda x: x['count'], **kwargs):
        """
        getting all items
        :parameter items_process function returned list of items from result
        :parameter count_process function returned one digit equals of count from result
        :returns list of all items
        """
        kwargs['count'] = batch_size
        first_result = self.get(method_name, **kwargs)
        result = items_process(first_result)
        count = count_process(first_result)
        iterations = count / batch_size if count > batch_size else 0

        for el in range(1, iterations + 1):
            kwargs['offset'] = el * batch_size
            next_result = items_process(self.get(method_name, **kwargs))
            result.extend(next_result)

        return result

    def get_friends(self, user_id):
        command = 'friends.get'
        kwargs = {'order': 'name',
                  'fields': vk_fields,
                  'user_id': user_id}
        result = self.get(command, **kwargs)
        return result

    def get_followers(self, user_id):
        command = 'users.getFollowers'
        kwargs = {
            'fields': vk_fields,
            'user_id': user_id}
        result = self.get_all(command, batch_size=1000, **kwargs)
        return result

    def get_posts(self, user_id):
        """
        Возвращает два списка: которые сделал сам юзер и те которые сделали ему.
        :param user_id:
        :return:
        """
        command = 'wall.get'
        kwargs = {'owner_id': user_id, 'filter': 'all', }
        result = self.get_all(command,
                              batch_size=100,
                              items_process=self.array_item_process,
                              count_process=self.array_count_process,
                              **kwargs)
        owners, others = [],[]
        for el in result:
            if el.get('from_id') == user_id:
                owners.append(el)
            else:
                others.append(el)
        return owners, others

    def get_notes(self, user_id):
        command = 'notes.get'
        kwargs = {'user_id': user_id, 'sort': 1}
        result = self.get_all(command,
                              batch_size=100,
                              items_process=self.array_item_process,
                              count_process=self.array_count_process,
                              **kwargs)
        return result

    def get_post_comments(self, post_id):
        """
        :param post_id: the identification of post from wall of user who have -
        :param owner_id: this id
        :return: array of comments with who, when and text information
        """
        command = 'wall.getComments'
        kwargs = {'post_id': post_id, 'need_likes': 1, 'sort': 'asc', 'preview_length': '0'}
        result = self.get_all(command,
                              batch_size=100,
                              items_process=self.array_item_process,
                              count_process=self.array_count_process,
                              **kwargs)
        APIMessage()
        return result

    def get_post_likers_ids(self, post_id):
        command = 'wall.getLikes'
        kwargs = {'post_id':post_id,}
        result = self.get_all(command,
                              batch_size=1000,
                              items_process=lambda x:x['users'],
                              count_process=lambda x:x['count'],
                              **kwargs)
        return [el['uid'] for el in result]


    @staticmethod
    def retrieve_mentions(text):
        prep = re.compile(u'\[id\d+\|').findall(text)
        mentions = [el[1:-1] for el in prep]
        return mentions if len(mentions) > 0 else None

    def get_user(self, user_id):
        """
        :param user_id: can be one id or some string of user ids with separate  is ','
        :return: vk_fields of user
        """
        command = 'users.get'
        kwargs = {'user_ids': user_id, 'fields': vk_fields}
        result = self.get(command, **kwargs)
        user = VK_APIUser(result[0])
        return user

    def get_users(self, uids):
        command= 'getProfiles'
        users = []
        for i in xrange((len(uids)/1000)+1):
            kwargs = {'uids':','.join([str(el) for el in uids[i*1000:(i+1)*1000]]), 'fields': vk_fields}
            result = self.get(command, **kwargs)
            for el in result:
                users.append(VK_APIUser(el))
        return users

    def search(self, q):
        """
        :param q:
        :return:
        """
        command = 'newsfeed.search'
        kwargs = {'extended': 1, 'q': q, 'count': 1000}
        result = self.get(command, **kwargs)
        return result[1:]

class VK_APIUser(APIUser):
    def __init__(self, data_dict, created_at_format=None, from_db=False):
        data_dict['sn_id'] = data_dict.pop('uid')
        if data_dict.get('bdate'):
            bdate = data_dict.get('bdate')
            if len(bdate) > 4:
                data_dict['bdate'] = datetime.datetime.strptime(bdate,'%d.%m.%Y')
        if data_dict.get('last_seen'):
            data_dict['last_seen'] = datetime.datetime.fromtimestamp(data_dict['last_seen']['time'])
        if data_dict.get('counters'):
            counters = data_dict.get('counters')
            data_dict['followers_count'] = counters['followers']
            data_dict['friends_count'] = counters['friends']
        data_dict['name'] = data_dict['first_name']+' '+data_dict['last_name']

        super(VK_APIUser, self).__init__(data_dict, created_at_format, from_db)

class TTR_APIMessage(APIMessage):
    def __init__(self, data_dict, created_at_format=None, from_db=False):
        user = {'sn_id':data_dict['uid']}
        super(TTR_APIMessage, self).__init__(data_dict, created_at_format, from_db)


if __name__ == '__main__':
    vk = VK_API()
    user = vk.get_user(user_id='pafnutij_akak')
    users = vk.get_users(['from_to_where', 'dm', 512])
    uid = user.sn_id
    owners, others = vk.get_posts(uid)
    # posts = vk.get_posts('dm')
    # followers = vk.get_followers('dm')
    # followers = vk.get_followers(uid)
    likers = vk.get_post_likers_ids(owners[0]['id'])
    comments = vk.get_post_comments(owners[0]['id'])
    # print likers, comments
