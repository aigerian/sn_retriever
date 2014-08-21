# coding=utf-8
import datetime
import random
from time import sleep
from properties import certs_path, vk_access_credentials, vk_login, vk_pass, vk_fields, logger, sleep_time_short, \
    vk_logins
from contrib.api.entities import API, APIException, APIUser, APIMessage, APISocialObject

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

error_codes = {180: 'note not found'}


class AccessTokenHolder(object):
    def __init__(self):
        self.log = logger.getChild('VK_API_token_holder')
        self.tokens = {}
        for el in vk_logins.itervalues():
            token = self.__auth(el)
            self.tokens[token['access_token']] = token

    def get_token(self, used_token=None):
        if used_token:
            self.tokens[used_token]['last_used'] = datetime.datetime.now()
        candidates = {}
        for token in self.tokens.itervalues():
            if 'last_used' in token:
                last_used = token.get('last_used')
            else:
                last_used = datetime.datetime(2013,
                                              random.randint(1, 12),
                                              random.randint(1, 28),
                                              random.randint(1, 23),
                                              random.randint(1, 59),
                                              random.randint(1, 59)
                )
            not_used_time = (datetime.datetime.now() - last_used).total_seconds()
            candidates[not_used_time] = token
        times = candidates.keys()
        times.sort()
        delta = sleep_time_short() - times[-1]
        if delta > 0:
            self.log.info('will sleep %s seconds' % (times[-1] - delta))
            sleep(abs(times[-1] - delta))
        result_token = self.__check_for_update(candidates[times[-1]])
        return result_token['access_token']

    def __auth(self, vk_login):
        """
        authenticate in vk with dirty hacks
        :return: access token
        """
        # process first page
        self.log.info('vkontakte authenticate for %s' % vk_login)
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
        access_token['init_time'] = datetime.datetime.now()
        access_token['expires_in'] = float(access_token['expires_in'])
        access_token['login'] = vk_login
        self.log.info('get access token: \n%s' % access_token)
        return access_token

    def __check_for_update(self, token):
        if (datetime.datetime.now() - token['init_time']).total_seconds() > token['expires_in']:
            old_token = self.tokens.pop(token['access_token'])
            new_token = self.__auth(old_token['login'])
            self.tokens[new_token['access_token']] = new_token
            return new_token
        return token


class VK_API(API):
    def __init__(self):
        self.log = logger.getChild('VK_API')
        self.token_holder = AccessTokenHolder()
        self.access_token = self.token_holder.get_token()
        self.base_url = 'https://api.vk.com/method/'
        self.array_item_process = lambda x: x[1:]
        self.array_count_process = lambda x: x[0]


    def get(self, method_name, **kwargs):
        while 1:
            params = dict({'access_token': self.access_token}, **kwargs)
            result = requests.get('%s%s' % (self.base_url, method_name), params=params)
            result_object = json.loads(result.content)
            if 'error' in result_object:
                if result_object['error']['error_code'] == 6:
                    # change access token and try
                    self.log.info('will change access token for \nmethod: %s\nparams: %s' % (method_name, str(kwargs)))
                    self.access_token = self.token_holder.get_token(self.access_token)
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
        try:
            result = self.get_all(command,
                                  batch_size=1000,
                                  items_process=lambda x: x['users'],
                                  count_process=lambda x: x['count'],
                                  **kwargs)
            return result
        except APIException as e:
            self.log.error(e)
            self.log.info('can not load likers ids for %s' % object_type)


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

    def _fill_comment_likers(self, comments):
        """
        Заполняем комментарии идентификаторами лайкнувших
        :param comments:
        """
        for comment in comments:
            if comment['likes']['count'] != 0:
                try:
                    comment['likers'] = self.get_likers_ids('comment', comment['user']['sn_id'], comment.sn_id)
                except APIException as e:
                    self.log.error(e)
                    self.log.info('can not load comment likes for comment %s' % comment.sn_id)

    def get_photos(self, user_id):
        comments = []
        result = []

        try:
            photo_result = self.get_all("photos.getAll", batch_size=200,
                                        items_process=self.array_item_process,
                                        count_process=self.array_count_process,
                                        **{'owner_id': user_id,
                                           'extended': 1,
                                           'photo_sizes': 0,
                                           'no_service_albums': 0})

            for photo_el in photo_result:
                photo_el['sn_id'] = "_".join(['photo', str(user_id), str(photo_el['pid'])])
                if photo_el.get('likes').get('count') != 0:
                    photo_el['likers'] = self.get_likers_ids('photo', user_id, photo_el['pid'])
                result.append(APISocialObject(photo_el))

                photo_comments = self.get_comments(user_id, photo_el['pid'], 'photo')
                self._fill_comment_likers(photo_comments)
                comments.extend(photo_comments)
        except APIException as e:
            self.log.exception(e)
            self.log.info('can not load comments/likers of photos for user_id: %s\nbecause:%s' % (user_id, e))

        return result, comments


    def get_videos(self, user_id):
        comments = []
        result = []

        try:
            video_result = self.get_all('video.get',
                                        batch_size=100,
                                        items_process=self.array_item_process,
                                        count_process=self.array_count_process,
                                        **{'owner_id': user_id, 'extended': 1})
            for video_el in video_result:
                video_el['sn_id'] = "_".join(['video', str(user_id), str(video_el['vid'])])
                if video_el.get('likes').get('count') != 0:
                    video_likers = self.get_likers_ids('video', user_id, video_el['vid'])
                    video_el['likers'] = video_likers
                result.append(APISocialObject(video_el))

                if video_el.get('comments') != 0:
                    video_comments = self.get_comments(user_id, video_el['vid'], 'video')
                    self._fill_comment_likers(video_comments)
                    comments.extend(video_comments)

        except APIException as e:
            self.log.exception(e)
            self.log.info('can not load comments/likers of videos for user_id: %s\nbecause:%s' % (user_id, e))

        return result, comments


    def get_notes(self, user_id):
        notes_result = []
        comments = []

        try:
            command = 'notes.get'
            kwargs = {'user_id': user_id, 'sort': 1}
            result = self.get_all(command,
                                  batch_size=100,
                                  items_process=self.array_item_process,
                                  count_process=self.array_count_process,
                                  **kwargs)
            for note_el in result:
                if 'nid' in note_el:
                    note_el['id'] = note_el.pop('nid')
                note = VK_APIMessage(note_el)
                notes_result.append(note)

                if note_el['ncom'] != 0:
                    note_comments = self.get_comments(user_id, note_el['id'], 'note')
                    self._fill_comment_likers(note_comments)
                    comments.extend(note_comments)

        except APIException as e:
            self.log.exception(e)
            self.log.info('can not load comments/likers of notes for user_id: %s\nbecause:%s' % (user_id, e))

        return notes_result, comments

    def get_wall_posts(self, user_id):
        """
        :param user_id:
        :return:
        """
        wall_post_result = []
        comments = []

        try:
            command = 'wall.get'
            kwargs = {'owner_id': user_id, 'filter': 'all', }
            result = self.get_all(command,
                                  batch_size=100,
                                  items_process=self.array_item_process,
                                  count_process=self.array_count_process,
                                  **kwargs)
            for wall_post in result:
                wall_post['sn_id'] = '_'.join(['wall', str(user_id), str(wall_post['id'])])
                post = VK_APIMessage(wall_post)
                if wall_post['likes']['count'] != 0:
                    wall_post_likers = self.get_likers_ids('post', user_id, post['id'])
                    post['likers'] = wall_post_likers

                wall_post_result.append(post)

                if post['comments']['count'] != 0:
                    wall_post_comments = self.get_comments(user_id, post['id'], 'wall')
                    self._fill_comment_likers(wall_post_comments)
                    comments.extend(wall_post_comments)

        except APIException as e:
            self.log.info('can not load comments/likers of wall posts for user_id: %s\nbecause:%s' % (user_id, e))

        return wall_post_result, comments

    def get_content_entities(self, user_id):
        """
        Возвращает объекты фотографий, видео, записок и записей на стене с идентификаторами лайкнувших людей
        а также, комментарии (также с идентификаторами лайкнувших)

        :param user_id: идентификатор пользователя (int)
        :return:
        """

        def retrieve_likers(objects):
            result = []
            for el in objects:
                result.extend(el.get('likers', []))
            return result

        entities = {}
        comments = []
        likers = []

        photos, photos_comments = self.get_photos(user_id)
        entities['photos'] = photos
        comments.extend(photos_comments)
        likers.extend(retrieve_likers(photos))
        likers.extend(retrieve_likers(photos_comments))

        videos, videos_comments = self.get_videos(user_id)
        entities['videos'] = videos
        comments.extend(videos_comments)
        likers.extend(retrieve_likers(videos))
        likers.extend(retrieve_likers(videos_comments))

        notes, notes_comments = self.get_notes(user_id)
        entities['notes'] = notes
        comments.extend(notes_comments)
        likers.extend(retrieve_likers(notes))
        likers.extend(retrieve_likers(notes_comments))

        wall_posts, wall_posts_comments = self.get_wall_posts(user_id)
        entities['wall_posts'] = wall_posts
        comments.extend(wall_posts_comments)
        likers.extend(retrieve_likers(wall_posts))
        likers.extend(retrieve_likers(wall_posts_comments))

        return entities, comments, list(set(likers))


class VK_APIUser(APIUser):
    def __init__(self, data_dict, created_at_format=None, ):
        data_dict['source'] = 'vk'
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
        super(VK_APIUser, self).__init__(data_dict, created_at_format)


class VK_APIMessage(APIMessage):
    def __init__(self, data_dict, created_at_format=None, comment_for=None):
        data_dict['source'] = 'vk'
        data_dict['user'] = {'sn_id': data_dict.pop('from_id', None) or data_dict.get('uid', None)}
        if not 'sn_id' in data_dict:
            data_dict['sn_id'] = data_dict.pop('cid', None) or data_dict.pop('id', None)
        data_dict['created_at'] = datetime.datetime.fromtimestamp(int(data_dict.pop('date')))
        if comment_for:
            data_dict['comment_for'] = comment_for
        super(VK_APIMessage, self).__init__(data_dict)


if __name__ == '__main__':
    api = VK_API()
    user = api.get_user('pafnutij_akak')
    entities, likers = api.get_content_entities(user.sn_id)
    print likers
