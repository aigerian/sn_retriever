# coding=utf-8
__author__ = '4ikist'

import datetime
import random
from time import sleep
import json
import re
import urlparse
from lxml import html
import requests

from properties import certs_path, vk_access_credentials, vk_pass, vk_user_fields, logger, sleep_time_short, \
    vk_logins, vk_group_fields
from contrib.api.entities import API, APIException, APIUser, APIMessage, APIContentObject, APISocialObject


def r(string):
    return string.replace('<br>', '\n')


user_id_re = re.compile('id\d+')


def get_mentioned(text):
    """
    находит все идентификаторы в тексте такие: [id1234567|Имя Фамилия] либо нормальные
    :param text: в чем искать
    :return: список 1234567
    """
    return [el[3:-1] if 'id' in el else el[1:] for el in re.findall('\[id\d+\||\@[^ ]+', text)]


comments_names = {'wall': {'cmd': 'wall', 'id': 'post'},
                  'photo': {'cmd': 'photos', 'id': 'photo'},
                  'video': {'cmd': 'video', 'id': 'video'},
                  'note': {'cmd': 'notes', 'id': 'note'}}

error_codes = {180: 'note not found'}
unix_time = lambda x: datetime.datetime.fromtimestamp(int(x))


class AccessTokenHolder(object):
    def __init__(self):
        self.log = logger.getChild('VK_API_token_holder')
        self.tokens = {}
        for el in vk_logins.itervalues():
            token = self.__auth(el)
            self.tokens[token['access_token']] = token
        self.current_login = None

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
        self.current_login = result_token['login']
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
        if (datetime.datetime.now() - token['init_time']).total_seconds() > token['expires_in'] and token[
            'expires_in'] != 0:
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
        def change_token(e):
            self.log.info(
                'will change access token for \nmethod: %s\nparams: %s\nbecause: %s' % (method_name, str(kwargs), e))
            self.access_token = self.token_holder.get_token(self.access_token)

        while 1:
            params = dict({'access_token': self.access_token}, **kwargs)
            result = requests.get('%s%s' % (self.base_url, method_name), params=params)
            try:
                result_object = json.loads(result.content)
            except Exception as e:
                change_token(e)
                continue
            if 'error' in result_object:
                if result_object['error']['error_code'] == 6:
                    # change access token and try
                    change_token(result_object['error']['error_msg'])
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
                  'fields': vk_user_fields,
                  'user_id': user_id}
        result = self.get(command, **kwargs)
        return result

    def get_followers(self, user_id):
        command = 'users.getFollowers'
        kwargs = {
            'fields': vk_user_fields,
            'user_id': user_id}
        result = self.get_all(command, batch_size=1000, **kwargs)
        return result

    def get_subscriptions(self, user_id):
        command = 'subscriptions.get'
        result = self.get_all(command, batch_size=1000,
                              items_process=lambda x: x['users'],
                              **{'uid': user_id})
        return result

    def get_subscription_followers(self, user_id):
        command = 'subscriptions.getFollowers'
        result = self.get_all(command, batch_size=1000,
                              items_process=lambda x: x['users'],
                              **{'uid': user_id})
        return result

    def get_groups(self, user_id):
        def get_members(group_id):
            return self.get_all('groups.getMembers', batch_size=1000, items_process=lambda x: x['users'],
                                **{'sort': 'time_asc', 'gid': group_id})

        result = []
        command = 'groups.get'
        group_result = self.get_all(command, batch_size=1000,
                                    count_process=self.array_count_process,
                                    items_process=self.array_item_process,
                                    **{'uid': user_id,
                                       'extended': 1,
                                       'fields': vk_group_fields})
        for group in group_result:
            try:
                members = get_members(group['gid'])
                group['members'] = members
            except APIException as e:
                self.log.warn('can not load group members :( for group [%s]' % group.get('name'))
            group.pop('is_admin')
            group.pop('is_member')
            group['source'] = 'vk'
            result.append(APISocialObject({'sn_id': group['gid'],
                                           'private': group['is_closed'],
                                           'name': group['name'],
                                           'screen_name': group['screen_name'],
                                           'type': group['type'],
                                           'known_members': group['members'] if group.get('members') else [user_id]}))
        return result

    def get_group_data(self, group_id):
        message_results = []
        content_objects = []
        related_users = set()
        topic_result = self.get_all('board.getTopics', batch_size=100,
                                    count_process=lambda x: x['topics'][0],
                                    items_process=lambda x: x['topics'][1:],
                                    **{'group_id': group_id, 'order': 2,
                                       'preview_length': 0})
        for topic in topic_result:
            if topic['comments'] != 0:
                comments_result = self.get_all('board.getComments', batch_size=100,
                                               count_process=lambda x: x['comments'][0],
                                               items_process=lambda x: x['comments'][1:],
                                               **{'group_id': group_id, 'topic_id': topic.get('id') or topic.get('tid'),
                                                  'need_likes': 1, })
                for topic_comment in comments_result:
                    related_users.add(topic_comment['from_id'])
                    # if topic_comment['likes']['count'] != 0:
                    # topic_comment['likers'] = self.get_likers_ids('topic_comment', topic_comment['from_id'],
                    # topic_comment['id'])
                    message_results.append(
                        VK_APIMessage(
                            dict({'sn_id': "%s_%s" % (topic_comment['id'], topic.get('id') or topic.get('tid')),
                                  'comment_id': topic_comment['id']}, **topic_comment),
                            comment_for={'type': 'group_topic', 'group_id': group_id,
                                         'id': topic.get('id') or topic.get('tid')})
                    )
            content_objects.append(VK_APIContentObject({'sn_id': topic.get('id') or topic.get('tid'),
                                                        'text': topic['title'],
                                                        'create_date': unix_time(topic['created']),
                                                        'change_date': unix_time(topic['updated']),
                                                        'type': 'group_topic'}))
            related_users.add(topic['created_by'])

        return message_results, content_objects, list(related_users)

    def get_comments(self, owner_id, entity_id, entity_type='wall'):
        """
        Извлекает комментарии для сущности с идентификатором entity_id, сделанной пользователем с идентификатором entity_id
        и типом сущности (wall, note, video, photo)
        :param entity_id:
        :param owner_id:
        :return: список APIMessage у которых есть поле comment_for (для чего этот комментарий)
        а также sn_id который состоит 'user who create object _ object id _ comment id _ user who commented'
        """

        command = '%s.getComments' % comments_names[entity_type]['cmd']
        kwargs = {'owner_id': owner_id,
                  '%s_id' % comments_names[entity_type]['id']: entity_id,
                  'need_likes': 1, 'sort': 'desc', 'preview_length': '0'}
        if entity_type == 'note':
            kwargs.pop('need_likes')
            kwargs['sort'] = 1
        comment_result = self.get_all(command,
                                      batch_size=100,
                                      items_process=self.array_item_process,
                                      count_process=self.array_count_process,
                                      **kwargs)
        result = []
        for comment_el in comment_result:
            comment_el['sn_id'] = '%s_%s_%s_%s' % (
                owner_id, entity_id, comment_el.get('cid'), comment_el.get('from_id'))
            # comment_el['sn_id_description'] = 'user who create object, object id, comment id, user who commented'
            comment_el['text'] = comment_el.get('message') or comment_el.get('text')
            comment = VK_APIMessage(comment_el,
                                    comment_for={'type': entity_type, 'id': entity_id, 'owner_id': owner_id},
                                    comment_id=comment_el.get('cid'))
            comment['mentioned'] = get_mentioned(comment_el['text'])
            result.append(comment)
        return result

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
        kwargs = {'user_ids': user_id, 'fields': vk_user_fields}
        result = self.get(command, **kwargs)
        user = VK_APIUser(result[0])
        return user

    def get_users(self, uids):
        command = 'getProfiles'
        users = []
        for i in xrange((len(uids) / 1000) + 1):
            kwargs = {'uids': ','.join([str(el) for el in uids[i * 1000:(i + 1) * 1000]]), 'fields': vk_user_fields}
            result = self.get(command, **kwargs)
            for el in result:
                users.append(VK_APIUser(el))
        return users

    def _fill_comment_likers(self, comments, comment_type='comment'):
        """
        Заполняем комментарии идентификаторами лайкнувших
        :param comments:
        """
        likers = []
        for comment in comments:
            if comment['likes']['count'] != 0:
                try:
                    comment['likers'] = self.get_likers_ids(comment_type, comment['user']['sn_id'], comment.comment_id)
                    likers.extend(comment['likers'])
                    comment.pop('likes')
                except APIException as e:
                    self.log.error(e)
                    self.log.info('can not load comment likes for comment %s' % comment.sn_id)
        return likers

    def get_photos(self, user_id):
        """
        Возвращает фотографии, альбомы, комментарии и лайкнувших пользователей
        :param user_id:
        :return:
        """
        comments = []
        result = []
        related_users = {'comments': [], 'likes': [], 'mentioned': []}
        try:
            photo_result = self.get_all("photos.getAll", batch_size=200,
                                        items_process=self.array_item_process,
                                        count_process=self.array_count_process,
                                        **{'owner_id': user_id,
                                           'extended': 1,
                                           'photo_sizes': 1,
                                           'no_service_albums': 0})
            albums = set()
            for photo_el in photo_result:
                photo = VK_APIContentObject({'sn_id': photo_el.get('id') or photo_el.get('pid'),
                                             'type': 'photo',
                                             'user': {'sn_id': user_id},
                                             'parent_id': photo_el['aid'],
                                             'text': photo_el['text'],
                                             'create_date': unix_time(photo_el['created']),
                                             'url': photo_el['sizes'][-1]['src']})
                if photo_el.get('likes').get('count') != 0:
                    photo['likers'] = self.get_likers_ids('photo', user_id, photo.sn_id)
                    related_users['likes'].extend(photo['likers'])
                result.append(photo)
                if photo_el['aid'] > 0:
                    albums.add(photo_el['aid'])
                photo_comments = self.get_comments(user_id, photo.sn_id, 'photo')
                self._fill_comment_likers(photo_comments, 'photo_comment')
                comments.extend(photo_comments)
                related_users['comments'].extend([el.user_id for el in photo_comments])
                related_users['mentioned'].extend(get_mentioned(photo_el['text']))
            albums_result = self.get_all('photos.getAlbums', batch_size=100,
                                         count_process=lambda x: len(x), items_process=lambda x: x,
                                         **{'owner_id': user_id, 'album_ids': ','.join([str(el) for el in albums]),
                                            'need_system': 0, 'need_covers': 0, })
            for album in albums_result:
                result.append(VK_APIContentObject({'sn_id': album['aid'],
                                                   'type': 'photo_album',
                                                   'user': {'sn_id': user_id},
                                                   'text': '%s\n%s' % (album['title'], album.get('description')),
                                                   'create_date': unix_time(album['created']),
                                                   'change_date': unix_time(album['updated'])}))
                related_users['mentioned'].extend(get_mentioned(album['title'] + album.get('description')))
        except APIException as e:
            self.log.exception(e)
            self.log.info('can not load comments/likers of photos for user_id: %s\nbecause:%s' % (user_id, e))

        return result, comments, exclude_owner_from_related_users(related_users, user_id)


    def get_videos(self, user_id):
        comments = []
        result = []
        related_users = {'comments': [], 'likes': [], 'mentioned': []}
        try:
            video_result = self.get_all('video.get',
                                        batch_size=100,
                                        items_process=self.array_item_process,
                                        count_process=self.array_count_process,
                                        **{'owner_id': user_id, 'extended': 1})
            for video_el in video_result:
                video = VK_APIContentObject({'sn_id': video_el.get('id') or video_el.get('vid'),
                                             'type': 'video',
                                             'user': {'sn_id': user_id},
                                             'text': '%s\n%s' % (video_el['title'], video_el['description']),
                                             'create_date': unix_time(video_el['date'])
                })
                if video_el.get('likes').get('count') != 0:
                    video_likers = self.get_likers_ids('video', user_id, video.sn_id)
                    video['likers'] = video_likers
                    related_users['likes'].extend(video_likers)
                result.append(video)

                if video_el.get('comments') != 0:
                    video_comments = self.get_comments(user_id, video.sn_id, 'video')
                    self._fill_comment_likers(video_comments, 'video_comment')
                    comments.extend(video_comments)
                    related_users['comments'].extend([el.user_id for el in video_comments])
                related_users['mentioned'].extend(get_mentioned(video_el['title'] + video_el['description']))
        except APIException as e:
            self.log.exception(e)
            self.log.info('can not load comments/likers of videos for user_id: %s\nbecause:%s' % (user_id, e))

        return result, comments, exclude_owner_from_related_users(related_users, user_id)


    def get_notes(self, user_id):
        notes_result = []
        comments = []
        related_users = {'comments': [], 'mentioned': []}
        try:
            result = self.get_all('notes.get',
                                  batch_size=100,
                                  items_process=self.array_item_process,
                                  count_process=self.array_count_process,
                                  **{'user_id': user_id, 'sort': 1})
            for note_el in result:
                if 'nid' in note_el:
                    note_el['id'] = note_el.pop('nid')
                note = VK_APIMessage(note_el)
                notes_result.append(note)
                related_users['mentioned'].extend(get_mentioned(note.text))

                if note_el['ncom'] != 0:
                    note_comments = self.get_comments(user_id, note_el['id'], 'note')
                    self._fill_comment_likers(note_comments, 'note')
                    comments.extend(note_comments)
                    related_users['comments'].extend([el.user_id for el in note_comments])

        except APIException as e:
            self.log.exception(e)
            self.log.info('can not load comments/likers of notes for user_id: %s\nbecause:%s' % (user_id, e))

        return notes_result, comments, exclude_owner_from_related_users(related_users)

    def get_wall_posts(self, user_id):
        """
        Извлекает достойные посты со стены пользователя и преобразывавет в сущности системы, а именно:
        VK_APIMessage.
        Достойность измеряется наличием текста, комментариев или лайков.
        :param user_id: идентификатор пользователя
        :return: список сообщений со стены, комментарии к этим сообщениям, связанные пользователи с именем связи
        """

        def get_reposts(post_id):
            reposts = []
            result = self.get_all('wall.getReposts', batch_size=1000,
                                  count_process=lambda x: len(x['items']),
                                  items_process=lambda x: x['items'],
                                  **{'owner_id': user_id, 'post_id': post_id})
            for repost in result:
                reposts.append(
                    {'user': repost['from_id'], 'created': unix_time(repost['date']), 'text': repost['text']})
            return reposts

        wall_post_result = []
        comments = []
        related_users = {'likes': [], 'comments': [], 'reposts': [], 'mentioned': []}
        try:
            result = self.get_all('wall.get',
                                  batch_size=100,
                                  items_process=self.array_item_process,
                                  count_process=self.array_count_process,
                                  **{'owner_id': user_id, 'filter': 'all', })
            for wall_post in result:
                # если пост стоящий
                if len(wall_post['text']) > 0 or \
                                wall_post['reposts']['count'] > 0 or \
                                wall_post['likes']['count'] > 0 or \
                                wall_post['comments']['count'] > 0:

                    content_object = {'sn_id': '_'.join(['wall', str(user_id), str(wall_post['id'])]),
                                      'user': {'sn_id': user_id}, }

                    if wall_post['likes']['count'] != 0:
                        wall_post_likers = self.get_likers_ids('post', user_id, wall_post['id'])
                        content_object['likers'] = wall_post_likers
                        related_users['likes'].extend(wall_post_likers)
                    if wall_post['comments']['count'] != 0:
                        wall_post_comments = self.get_comments(user_id, wall_post['id'], 'wall')
                        related_users['comments'].extend([el.user_id for el in wall_post_comments])
                        self._fill_comment_likers(wall_post_comments)
                        comments.extend(wall_post_comments)
                        related_users['likes'].extend([el['likers'] for el in wall_post_comments if
                                                       el.user_id == user_id and el['likes']['count'] != 0])
                    if wall_post['reposts']['count'] != 0:
                        reposts = get_reposts(wall_post['id'])
                        content_object['reposts'] = reposts
                        related_users['reposts'].extend([el['user'] for el in reposts])
                    related_users['mentioned'].extend(get_mentioned(wall_post['text']))
                    post = VK_APIMessage(dict(content_object,
                                              **{'text': r(wall_post['text']),
                                                 'type': 'wall',
                                                 'post_id': wall_post['id'],
                                                 'date': wall_post['date']}))
                    wall_post_result.append(post)

        except APIException as e:
            self.log.info('can not load comments/likers of wall posts for user_id: %s\nbecause:%s' % (user_id, e))

        return wall_post_result, comments, exclude_owner_from_related_users(related_users, user_id)


def exclude_owner_from_related_users(related_users, owner_user_id):
    for k, v in related_users.iteritems():
        updated_list = list(set(v))
        if owner_user_id in updated_list:
            updated_list.remove(owner_user_id)
        related_users[k] = updated_list
    return related_users


class VK_APIUser(APIUser):
    def __init__(self, data_dict, created_at_format=None, ):
        data_dict['source'] = 'vk'
        data_dict['sn_id'] = data_dict.pop('uid')
        if data_dict.get('bdate'):
            bdate = data_dict.get('bdate')
            if len(bdate) > 4:
                data_dict['bdate'] = datetime.datetime.strptime(bdate, '%d.%m.%Y')
        if data_dict.get('last_seen'):
            data_dict['last_seen'] = unix_time(data_dict['last_seen']['time'])
        if data_dict.get('counters'):
            counters = data_dict.get('counters')
            data_dict['followers_count'] = counters['followers']
            data_dict['friends_count'] = counters['friends']
        data_dict['name'] = data_dict['first_name'] + ' ' + data_dict['last_name']
        super(VK_APIUser, self).__init__(data_dict, created_at_format)


class VK_APIMessage(APIMessage):
    def __init__(self, data_dict, created_at_format=None, comment_for=None, comment_id=None):
        data_dict.pop('cid', None)
        data_dict.pop('online', None)
        data_dict.pop('uid', None)
        data_dict['source'] = 'vk'
        if data_dict.get('user', None) is None:
            data_dict['user'] = {'sn_id': data_dict.pop('from_id', None) or data_dict.get('uid', None)}
        if not 'sn_id' in data_dict:
            data_dict['sn_id'] = data_dict.pop('cid', None) or data_dict.pop('id', None)
        data_dict['created_at'] = datetime.datetime.fromtimestamp(int(data_dict.pop('date')))
        if comment_for:
            data_dict['comment_for'] = comment_for
            data_dict['comment_id'] = comment_id
        super(VK_APIMessage, self).__init__(data_dict)

    @property
    def comment_id(self):
        return self.get('comment_id')


class VK_APIContentObject(APIContentObject):
    def __init__(self, data_dict):
        data_dict['source'] = 'vk'
        super(VK_APIContentObject, self).__init__(data_dict)


if __name__ == '__main__':
    api = VK_API()
    user = api.get_user('266544674')
    # for test video10130611_168906403
    # entities, comments, likers = api.get_content_entities(user.sn_id)
    # followers = api.get_followers(user.sn_id)
    # user_subscript = api.get_subscriptions(user.sn_id)
    # subscript_of_user = api.get_subscription_followers(user.sn_id)
    groups = api.get_groups(user.sn_id)
    # videos = api.get_videos(user.sn_id)
    # photos = api.get_photos(user.sn_id)
    # wall_posts = api.get_wall_posts(user.sn_id)
    for group in groups:
        so, com, ru = api.get_group_data(group.sn_id)
        print so, com, ru


