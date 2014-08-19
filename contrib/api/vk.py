# coding=utf-8
import datetime
from time import sleep
from properties import certs_path, vk_access_credentials, vk_login, vk_pass, vk_fields, logger, sleep_time_long, \
    sleep_time_short
from contrib.api.entities import API, APIException, APIUser, APIMessage

import json
import re
import urlparse

from lxml import html
import requests

__author__ = '4ikist'

comments_names = {'wall': {'cmd': 'wall', 'id': 'post'},
                  'photo': {'cmd': 'photos', 'id': 'photo'},
                  'video': {'cmd': 'video', 'id': 'video'},
                  'note': {'cmd': 'notes', 'id': 'note'}}


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
        # process first page
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
        # process second page
        result = s.post(form_url, form_params)
        doc = html.document_fromstring(result.content)
        # if already login
        if 'OAuth Blank' not in doc.xpath('//title')[0].text:
            submit_url = doc.xpath('//form')[0].attrib.get('action')
            result = s.post(submit_url, cookies=result.cookies)

        # retrieving access token from url
        parsed_url = urlparse.urlparse(result.url)
        if 'error' in parsed_url.query:
            self.log.error('error in authenticate \n%s' % parsed_url.query)
            raise APIException(dict([el.split('=') for el in parsed_url.query.split('&')]))

        fragment = parsed_url.fragment
        access_token = dict([el.split('=') for el in fragment.split('&')])
        self.log.info('get access token: \n%s' % access_token)
        return access_token

    def get(self, method_name, **kwargs):
        while 1:
            params = dict({'access_token': self.access_token['access_token']}, **kwargs)
            result = requests.get('%s%s' % (self.base_url, method_name), params=params)
            result_object = json.loads(result.content)
            if 'error' in result_object:
                if result_object['error']['error_code'] == 6:
                    stime = sleep_time_short()
                    self.log.info('will sleep %s seconds \n[%s]\n%s' % (stime, method_name, str(kwargs)))
                    sleep(stime)
                    continue
                else:
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

    def get_wall_posts(self, user_id):
        """
        Возвращает два списка постов: которые сделал сам юзер и те которые сделали ему другие на стену.
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
        return [VK_APIMessage(el) for el in result]

    def get_notes(self, user_id):
        command = 'notes.get'
        kwargs = {'user_id': user_id, 'sort': 1}
        result = self.get_all(command,
                              batch_size=100,
                              items_process=self.array_item_process,
                              count_process=self.array_count_process,
                              **kwargs)
        for el in result:
            el['id'] = el.pop('nid') if 'nid' in el else el.get('id')

        return [VK_APIMessage(el) for el in result]

    def get_comments(self, owner_id, entity_id, entity_type='wall'):
        """
        :param entity_id: the identification of post from wall of user who have -
        :param owner_id: this id
        :return: array of comments with who, when and text information
        """

        command = '%s.getComments' % comments_names[entity_type]['cmd']
        kwargs = {'owner_id': owner_id,
                  '%s_id' % comments_names[entity_type]['id']: entity_id,
                  'need_likes': 1, 'sort': 'desc', 'preview_length': '0'}
        if entity_type == 'note':
            kwargs.pop('need_likes')
            kwargs['sort'] = 1
        result = self.get_all(command,
                              batch_size=100,
                              items_process=self.array_item_process,
                              count_process=self.array_count_process,
                              **kwargs)
        return [VK_APIMessage(el, comment_for={'type': entity_type, 'id': entity_id, 'owner_id': owner_id}) for el in
                result]

    def get_likers_ids(self, object_type, owner_id, item_id, is_community=False):
        command = 'likes.getList'
        kwargs = {'type': object_type,
                  'owner_id': owner_id if not is_community else -owner_id,
                  'item_id': item_id,
                  'friends_only': 0,
                  'extended': 0}

        result = self.get_all(command,
                              batch_size=1000,
                              items_process=lambda x: x['users'],
                              count_process=lambda x: x['count'],
                              **kwargs)
        return result


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
        command = 'getProfiles'
        users = []
        for i in xrange((len(uids) / 1000) + 1):
            kwargs = {'uids': ','.join([str(el) for el in uids[i * 1000:(i + 1) * 1000]]), 'fields': vk_fields}
            result = self.get(command, **kwargs)
            for el in result:
                users.append(VK_APIUser(el))
        return users

    def get_comment_likers(self, comments):
        result = {}
        for comment in comments:
            if comment['likes']['count'] != 0:
                try:
                    result[comment.sn_id] = self.get_likers_ids('comment', comment['user']['sn_id'], comment.sn_id)
                except APIException:
                    pass
        return result

    def get_content_entities(self, user_id):
        """
        Возвращает все текстовые данные которые связанны с пользователем
        (посты на стене, заметки, видео/фото комментарии).
        А также идентификаторы лайкнувших это все, и лайкнувших комменты
        А также идентификаторы объектов которые пользователь нагенерил (либо добавил к себе)
        За исключением групп

        :param user_id: идентификатор пользователя (int)
        :return:
        """

        def fill_likers_by_comments(likers, comments):
            likers.extend(
                reduce(lambda acc, x: acc + x,
                       self.get_comment_likers(wall_post_comments).itervalues(),
                    []))

        likers = []
        messages = []
        content_object_ids = {'photo': [], 'video': [], 'note': [], 'wall_post': []}
        try:
            photo_result = self.get_all("photos.getAll", batch_size=200,
            items_process=self.array_item_process,
                                            count_process=self.array_count_process,
                                            **{'owner_id': user_id,
                                               'extended': 1,
                                               'photo_sizes': 0,
                                               'no_service_albums': 0})

            for photo_el in photo_result:
                content_object_ids['photo'].append(photo_el['pid'])
                photo_comments = self.get_comments(user_id, photo_el['pid'], 'photo')
                fill_likers_by_comments(likers,photo_comments)
                messages.extend(photo_comments)
                if photo_el.get('likes').get('count') != 0:
                    photo_likers = self.get_likers_ids('photo', user_id, photo_el['pid'])
                    likers.extend(photo_likers)
        except APIException as e:
            self.log.info('can not load comments/likers of photos for user_id: %s\nbecause:%s' % (user_id, e))
        #
        try:
            video_result = self.get_all('video.get',
                                        batch_size=100,
                                        items_process=self.array_item_process,
                                        count_process=self.array_count_process,
                                        **{'owner_id': user_id, 'extended': 1})
            for video_el in video_result:
                content_object_ids['video'].append(video_el['vid'])
                if video_el.get('comments') != 0:
                    video_comments = self.get_comments(user_id, video_el['vid'], 'video')
                    fill_likers_by_comments(likers,video_comments)
                    messages.extend(video_comments)
                if video_el.get('likes').get('count') != 0:
                    video_likers = self.get_likers_ids('video', user_id, video_el['vid'])
                    likers.extend(video_likers)
        except APIException as e:
            self.log.info('can not load comments/likers of videos for user_id: %s\nbecause:%s' % (user_id, e))

        try:
            notes_result = self.get_notes(user_id)
            for note_el in notes_result:
                content_object_ids['note'].append(note_el.sn_id)
                messages.append(note_el)
                if note_el['ncom'] != 0:
                    note_comments = self.get_comments(user_id, note_el.sn_id, 'note')
                    messages.extend(note_comments)
        except APIException as e:
            self.log.info('can not load comments/likers of notes for user_id: %s\nbecause:%s' % (user_id, e))

        try:
            wall_posts = self.get_wall_posts(user_id)
            for wall_post in wall_posts:
                messages.append(wall_post)
                content_object_ids['wall_post'].append(wall_post.sn_id)
                if wall_post['comments']['count'] != 0:
                    wall_post_comments = self.get_comments(user_id, wall_post.sn_id, 'wall')
                    fill_likers_by_comments(likers, wall_post_comments)
                    messages.extend(wall_post_comments)
                if wall_post['likes']['count'] != 0:
                    wall_post_likers = self.get_likers_ids('wall', user_id, wall_post.sn_id)
                    likers.extend(wall_post_likers)
        except APIException as e:
            self.log.info('can not load comments/likers of notes for user_id: %s\nbecause:%s' % (user_id, e))

        return messages, list(set(likers)), content_object_ids

    def search(self, q):
        """
        :param q:
        kwargs = {'extended': 1, 'q': q, 'count': 1000}
        result = self.get(command, **kwargs)
        return result[1:]
        :return:
        """
        command = 'newsfeed.search'


class VK_APIUser(APIUser):
    def __init__(self, data_dict, created_at_format=None, from_db=False):
        if not from_db:
            data_dict['sn_id'] = data_dict.pop('uid')
            if data_dict.get('bdate'):
                bdate = data_dict.get('bdate')
                if len(bdate) > 4:
                    data_dict['bdate'] = datetime.datetime.strptime(bdate, '%d.%m.%Y')
            if data_dict.get('last_seen'):
                data_dict['last_seen'] = datetime.datetime.fromtimestamp(data_dict['last_seen']['time'])
            if data_dict.get('counters'):
                counters = data_dict.get('counters')
                data_dict['followers_count'] = counters['followers']
                data_dict['friends_count'] = counters['friends']
            data_dict['name'] = data_dict['first_name'] + ' ' + data_dict['last_name']
        super(VK_APIUser, self).__init__(data_dict, created_at_format, from_db)


class VK_APIMessage(APIMessage):
    def __init__(self, data_dict, created_at_format=None, comment_for=None):
        data_dict['user'] = {'sn_id': data_dict.pop('from_id', None) or data_dict.get('uid', None)}
        data_dict['sn_id'] = data_dict.pop('cid', None) or data_dict.pop('id', None)
        data_dict['created_at'] = datetime.datetime.fromtimestamp(int(data_dict.pop('date')))
        if comment_for:
            data_dict['comment_for'] = comment_for
        super(VK_APIMessage, self).__init__(data_dict)


if __name__ == '__main__':
    vk = VK_API()
    user = vk.get_user(user_id='51600')
    # users = vk.get_users(['from_to_where', 'dm', 512])
    uid = user.sn_id
    # posts = vk.get_wall_posts(uid)
    # posts = vk.get_posts('dm')
    # followers = vk.get_followers('dm')
    # followers = vk.get_followers(uid)
    # post_likers = vk.get_likers_ids('post', user.sn_id, owners[0].sn_id)
    # comments = vk.get_post_comments(owners[0]['sn_id'])
    # comment_likers = vk.get_likers_ids('comment', user.sn_id, comments[0].sn_id)
    # print post_likers, comment_likers, comments
    result = vk.get_content_entities(uid)