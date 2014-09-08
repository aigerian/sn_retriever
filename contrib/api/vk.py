# coding=utf-8
from itertools import chain

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

member_type_rel = ('member', 'request', 'invitation')


def get_mentioned(text):
    """
    находит все идентификаторы в тексте такие: [id1234567|Имя Фамилия]
    :param text: в чем искать
    :return: список 1234567
    """
    if text is not None:
        return [el[3:-1] if 'id' in el else el[1:] for el in re.findall('\[id\d+\|?\:?', text)]
    return []


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
            self.log.info('will sleep %s seconds' % abs(times[-1] - delta))
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
            self.log.info('now access token by user: %s [%s]' % (self.access_token, self.token_holder.current_login))

        change_token_succession = 0
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
                    # if many request per second
                    change_token(result_object['error']['error_msg'])
                    continue
                elif result_object['error']['error_code'] == 7:
                    # if permission denied
                    if change_token_succession >= len(vk_logins):
                        raise APIException(result_object)
                    else:
                        change_token_succession += 1
                    change_token(result_object['error']['error_msg'])
                    continue
                else:
                    raise APIException(result_object)
            return result_object['response']

    def get_all(self, method_name, batch_size=200, items_process=lambda x: x['items'],
                count_process=lambda x: x['count'], **kwargs):
        """
        getting all items by batch size
        :parameter items_process function returned list of items from result
        :parameter count_process function returned one digit equals of count from result
        :returns generator by all items
        """
        kwargs['count'] = batch_size
        first_result = self.get(method_name, **kwargs)
        if not len(first_result):
            return
        result = items_process(first_result)
        count = count_process(first_result)
        iterations = count / batch_size if count > batch_size else 0
        for el in result:
            yield el
        for el in range(1, iterations + 1):
            kwargs['offset'] = el * batch_size
            next_result = items_process(self.get(method_name, **kwargs))
            for el in next_result:
                yield el

    def get_friends(self, user_id):
        command = 'friends.get'
        kwargs = {'order': 'name',
                  'fields': vk_user_fields,
                  'user_id': user_id}
        result = self.get_all(command, batch_size=100, items_process=lambda x: x, count_process=lambda x: len(x),
                              **kwargs)
        return [VK_APIUser(el) for el in result]

    def get_followers(self, user_id):
        command = 'users.getFollowers'
        kwargs = {
            'fields': vk_user_fields,
            'user_id': user_id}
        result = self.get_all(command, batch_size=100, **kwargs)
        return [VK_APIUser(el) for el in result]

    def get_subscriptions(self, user_id):
        command = 'subscriptions.get'
        result = self.get_all(command, batch_size=100,
                              items_process=lambda x: x['users'],
                              **{'uid': user_id})
        return [VK_APIUser(el) for el in result]

    def get_subscription_followers(self, user_id):
        """
        тоже самое что и followers только возвращает идишники
        :param user_id:
        :return: sn_ids of subscription followers
        """
        command = 'subscriptions.getFollowers'
        result = self.get_all(command, batch_size=1000,
                              items_process=lambda x: x['users'],
                              **{'uid': user_id})
        return list(result)

    def get_groups(self, user_id):
        def get_members(group_id):
            return list(self.get_all('groups.getMembers', batch_size=1000, items_process=lambda x: x['users'],
                                     **{'sort': 'time_asc', 'gid': group_id}))

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
            result.append(APISocialObject({'sn_id': group['gid'],
                                           'private': group['is_closed'],
                                           'name': group['name'],
                                           'screen_name': group['screen_name'],
                                           'type': group['type'],
                                           'source': 'vk'
            }))
        return result

    def check_members(self, candidates, group_id):
        relations = []
        for commentators_batch_name in _take_by(candidates, 500):
            is_members_result = self.get('groups.isMember', user_ids=commentators_batch_name, group_id=group_id,
                                         extended=1)
            for el in is_members_result:
                relation_type_ = [k for k, v in el.iteritems() if v == 1 and k in member_type_rel]
                if len(relation_type_):
                    relations.append((el['user_id'], relation_type_[0], group_id))
        return relations

    def get_group_topic_comments(self, group_id, topic_id, topic_user_id):
        """
        Извлекает комментарии к топику в группе
        :param group_id:  идентификатор группы
        :param topic_id:  идентификатор топика
        :param topic_user_id:  идентификатор пользователя создавшего топик
        :return: два массива:
        """
        contentResult = ContentResult()
        comments_result = self.get_all('board.getComments', batch_size=100,
                                       count_process=lambda x: x['comments'][0],
                                       items_process=lambda x: x['comments'][1:],
                                       **{'group_id': group_id, 'topic_id': topic_id,
                                          'need_likes': 1, })
        commentators = []
        for topic_comment in comments_result:
            topic_comment_user_id = topic_comment['from_id']
            commentators.append(topic_comment_user_id)
            contentResult.add_relations((topic_comment_user_id, 'comment', topic_user_id))
            contentResult.add_relations(
                [(topic_comment_user_id, 'mention', el) for el in get_mentioned(topic_comment['text'])])
            contentResult.add_comments(
                VK_APIMessage(
                    dict({'sn_id': "%s_%s_%s" % (topic_comment['id'], topic_id, group_id),
                          'comment_id': topic_comment['id']}, **topic_comment),
                    comment_for={'sn_id': topic_id})
            )
            contentResult.add_relations(
                [(topic_comment_user_id, 'mentioned', el) for el in get_mentioned(topic_comment['text'])])

        contentResult.add_relations(self.check_members(commentators, group_id))
        return contentResult

    def get_group_data(self, group_id):
        """
        Вовращает данные находящиеся в группе
        :param group_id:
        :return:
        """
        contentResult = ContentResult()
        # load group topics and comments
        topic_result = self.get_all('board.getTopics', batch_size=100,
                                    count_process=lambda x: x['topics'][0],
                                    items_process=lambda x: x['topics'][1:],
                                    **{'group_id': group_id, 'order': 2,
                                       'preview_length': 0})
        for topic in topic_result:
            topic_user_id = topic.get('created_by')
            topic_id = topic.get('id') or topic.get('tid')
            if topic['comments'] != 0:
                topic_comments_result = self.get_group_topic_comments(group_id, topic_id, topic_user_id)
                contentResult += topic_comments_result

            contentResult.add_content(VK_APIContentObject({'sn_id': topic.get('id') or topic.get('tid'),
                                                           'text': topic['title'] + '\n' + topic.get('text', ''),
                                                           'create_date': unix_time(topic['created']),
                                                           'change_date': unix_time(topic['updated']),
                                                           'type': 'group_topic',
                                                           'user': {'sn_id': topic_user_id}}))
        # load group photos
        photos_content_result = self.get_photos(-group_id)
        contentResult.add_relations(self.__get_members_from_result(photos_content_result.relations, contentResult.get_relations_with_type(member_type_rel,r=False), group_id))
        video_content_result = self.get_videos(-group_id)
        contentResult.add_relations(self.__get_members_from_result(video_content_result.relations, contentResult.get_relations_with_type(member_type_rel,r=False), group_id))
        contentResult+=photos_content_result+video_content_result

        return contentResult

    def __get_members_from_result(self, result_relations, saved_members, group_id):
        members_candidates = set([el[0 if int(el[2])<0 else 2] for el in result_relations])
        members_candidates.difference_update(saved_members)
        return self.check_members(list(members_candidates), group_id)

    def get_comments(self, owner_id, entity_id, entity_type='wall', parent_sn_id=None, load_likers=True):
        """
        Извлекает комментарии для сущности с идентификатором entity_id, сделанной пользователем с идентификатором entity_id
        и типом сущности (wall, note, video, photo)
        :param owner_id: идентификатор пользователя владельца сущности
        :param entity_id: идентификатор сущности
        :param entity_type: тип сущности
        :param parent_sn_id: идентификатор сущности для связи комментария с комментируемой сущностью
        :return:
        результирующий объект с заполненными comments и relations:
            список comments это APIMessage у которых есть поле comment_for (для чего этот комментарий),
        а также sn_id который состоит 'user who create object _ object id _ comment id _ user who commented'
            список relations включает в себя связи комментирующего и коментатора, упомянутых пользователей
        и лайкнувших пользователей
        """
        contentResult = ContentResult()
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
        for comment_el in comment_result:
            comment_id = comment_el.get('cid') or comment_el.get('id')
            comment_el['sn_id'] = '%s_%s_%s_%s' % (
                owner_id, entity_id, comment_id, comment_el.get('from_id'))
            comment_el['text'] = comment_el.get('message') or comment_el.get('text')
            comment = VK_APIMessage(comment_el,
                                    comment_for={'sn_id': parent_sn_id or entity_id},
                                    comment_id=comment_id)
            comment['mentions'] = get_mentioned(comment_el['text'])
            contentResult.add_comments(comment)
            contentResult.add_relations([(comment.user_id, 'mention', el) for el in comment['mentions']])
            contentResult.add_relations((comment.user_id, 'comment', owner_id))
            if comment['likes']['count'] > 0 and load_likers:
                contentResult.add_relations(self._fill_comment_likers(comment, (
                    '%s_comment' % entity_type) if entity_type != 'wall' else 'comment'))

        return contentResult

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
            return list(result)
        except APIException as e:
            self.log.error(e)
            self.log.info('can not load likers ids for %s' % object_type)

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

    def _fill_comment_likers(self, comment, comment_type='comment'):
        """
        Заполняем комментарии идентификаторами лайкнувших и возвращаем связи
        :param comments: собственно список комментариев
        :return список связей кто лайкнул комментарий
        """
        try:
            relations = []
            likers = self.get_likers_ids(comment_type, comment.user_id, comment.comment_id)
            if len(likers):
                comment['likers'] = likers
                relations.extend([(el, 'likes', comment.user_id) for el in comment['likers']])
            return relations
        except APIException as e:
            self.log.error(e)
            self.log.info('can not load comment likes for comment %s' % comment.sn_id)

    def get_photos(self, user_id):
        """
        Возвращает фотографии, альбомы, комментарии и связанных с каждым фото пользователей:
        те кто лайкнули это фото,
        те кто прокомментировали это фото,
        те кто упомянут в комментариях,
        те кто упомянут в описании к фото
        те кто упомянут в описании к альбому
        :param user_id: пользователь чьи фотографии (либо группа с -)
        :return:
         результирующий объект где есть:
        1) контент (APIContentObject) включающий объекты фотографий и альбомов,
        причем объекты фото имеют полу parent_id для связи с альбомом.
        2) комментарии (APIMessageObject)
        3) связи пльзователей от этих фотографий
        """
        contentResult = ContentResult()
        for_group = user_id < 0
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
                photo_owner = user_id if not for_group else photo_el['user_id']
                photo = VK_APIContentObject({'sn_id': photo_el.get('id') or photo_el.get('pid'),
                                             'type': 'photo',
                                             'user': {'sn_id': photo_owner},
                                             'parent_id': photo_el['aid'],
                                             'text': photo_el['text'],
                                             'create_date': unix_time(photo_el['created']),
                                             'url': photo_el['sizes'][-1]['src']})
                if for_group:
                    photo['group_id'] = user_id
                if photo_el.get('likes').get('count') != 0:
                    photo['likers'] = self.get_likers_ids('photo', user_id, photo.sn_id)
                    contentResult.add_relations([(el, 'likes', photo_owner) for el in photo['likers']])
                contentResult.add_content(photo)
                if photo_el['aid'] > 0:
                    albums.add(photo_el['aid'])
                photo_comments_result = self.get_comments(user_id, photo.sn_id, 'photo', load_likers=not for_group)
                contentResult += photo_comments_result
                contentResult.add_relations([(photo_owner, 'mention', el) for el in get_mentioned(photo_el['text'])])

            albums_result = self.get_all('photos.getAlbums', batch_size=100,
                                         count_process=lambda x: len(x), items_process=lambda x: x,
                                         **{'owner_id': user_id, 'album_ids': ','.join([str(el) for el in albums]),
                                            'need_system': 0, 'need_covers': 0, })
            for album in albums_result:
                contentResult.add_content(VK_APIContentObject({'sn_id': album['aid'],
                                                               'type': 'photo_album',
                                                               'user': {'sn_id': user_id},
                                                               'text': '%s\n%s' % (
                                                                   album['title'], album.get('description')),
                                                               'create_date': unix_time(album['created']),
                                                               'change_date': unix_time(album['updated'])}))
                contentResult.add_relations([(user_id, 'mention', el) for el in get_mentioned(album['title'])])
        except APIException as e:
            self.log.exception(e)
            self.log.info('can not load comments/likers of photos for user_id: %s\nbecause:%s' % (user_id, e))
        return contentResult

    def get_videos(self, user_id):
        """
        Возвращает видео и комментарии и связанных с каждым видео пользователей. А именно:
        те кто лайкнули это видео,
        те кто прокомментировали это видео,
        те кто упомянут в комментариях,
        те кто упомянут в описании к видео
        :param user_id: пользователь чьи видео (либо группа с -)
        :return: результирующий объект в котором 1) контент (APIContentObject) включающий объекты видео
        2) комментарии (APIMessageObject)
        3) связи пльзователей от этих видео
        """
        contentResult = ContentResult()
        for_group = user_id < 0
        try:
            video_result = self.get_all('video.get',
                                        batch_size=100,
                                        items_process=self.array_item_process,
                                        count_process=self.array_count_process,
                                        **{'owner_id': user_id, 'extended': 1})
            for video_el in video_result:
                video_owner_id = user_id if not for_group else video_el['user_id']
                video = VK_APIContentObject({'sn_id': video_el.get('id') or video_el.get('vid'),
                                             'type': 'video',
                                             'user': {'sn_id': video_owner_id},
                                             'text': '%s\n%s' % (video_el['title'], video_el['description']),
                                             'create_date': unix_time(video_el['date']),
                                             'comments_count': video_el['comments'],
                                             'views_count': video_el['views']
                })
                if for_group:
                    video['group_id'] = user_id
                if video_el.get('likes').get('count') != 0:
                    video['likers'] = self.get_likers_ids('video', user_id, video.sn_id)
                    contentResult.add_relations([(el, 'likes', video_owner_id) for el in video['likers']])
                if video_el.get('comments') != 0:
                    video_comments_result = self.get_comments(user_id, video.sn_id, 'video', load_likers=False)
                    contentResult += video_comments_result

                contentResult.add_relations(
                    [(video_owner_id, 'mention', el) for el in
                     get_mentioned(video_el['title'] + video_el['description'])])
                contentResult.add_content(video)

        except APIException as e:
            self.log.exception(e)
            self.log.info('can not load comments/likers of videos for user_id: %s\nbecause:%s' % (user_id, e))

        return contentResult

    def get_notes(self, user_id):
        """
        Возвращает информацию о записках пользователя, объект включающий себя:
        контент -  объекты собственно записок
        комментарии к запискам
        связи пользователей, комментирующих и упоямнутых в комментариях, в записке, лайкнувших комментари.
        :param user_id:
        :return:
        """
        contentResult = ContentResult()
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
                note['comments_count'] = int(note.pop('ncom'))
                contentResult.add_content(note)
                contentResult.add_relations([(user_id, 'mention', el) for el in get_mentioned(note.get('text'))])

                if note['comments_count'] != 0:
                    note_comments_result = self.get_comments(user_id, note.sn_id, 'note')
                    contentResult += note_comments_result

        except APIException as e:
            self.log.exception(e)
            self.log.info('can not load comments/likers of notes for user_id: %s\nbecause:%s' % (user_id, e))

        return contentResult

    def get_reposts(self, user_id, post_id):
        reposts = []
        result = self.get_all('wall.getReposts', batch_size=1000,
                              count_process=lambda x: len(x['items']),
                              items_process=lambda x: x['items'],
                              **{'owner_id': user_id, 'post_id': post_id})
        for repost in result:
            reposts.append(
                {'user': repost['from_id'], 'created': unix_time(repost['date']), 'text': repost['text']})
        return reposts

    def get_wall_posts(self, user_id):
        """
        Извлекает достойные посты со стены пользователя и преобразывавет в сущности системы, а именно:
        VK_APIMessage.
        Достойность измеряется наличием текста, комментариев или лайков.
        :param user_id: идентификатор пользователя
        :return: список сообщений со стены, комментарии к этим сообщениям, связанные пользователи с именем связи
        """
        contentResult = ContentResult()
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
                        contentResult.add_relations([(el, 'likes', user_id) for el in wall_post_likers])
                    if wall_post['comments']['count'] != 0:
                        wall_post_comments = self.get_comments(user_id, wall_post['id'], 'wall',
                                                               parent_sn_id=content_object['sn_id'])
                        contentResult += wall_post_comments
                    if wall_post['reposts']['count'] != 0:
                        reposts = self.get_reposts(user_id, wall_post['id'])
                        content_object['reposts'] = reposts
                        contentResult.add_relations([(el['user'], 'repost', user_id) for el in reposts])
                    contentResult.add_relations([(user_id, 'mentioned', el) for el in get_mentioned(wall_post['text'])])

                    post = VK_APIMessage(dict(content_object,
                                              **{'text': wall_post['text'],
                                                 'type': 'wall',
                                                 'post_id': wall_post['id'],
                                                 'date': wall_post['date']}))
                    contentResult.add_content(post)

        except APIException as e:
            self.log.info('can not load comments/likers of wall posts for user_id: %s\nbecause:%s' % (user_id, e))
        return contentResult



import html2text


def _process_text_fields(data):
    for key in ['text', 'title', 'message', 'description', ]:
        if key in data and data.get(key) is not None:
            data[key] = html2text.html2text(data[key]).strip()

def _delete_fields_with_prefix(data, prefixes, l=True,r=False):
    to_replace = []
    for k,v in data.iteritems():
        if isinstance(k, (str,unicode)):
            for prefix in prefixes:
                if l and k.startswith(prefix):
                    to_replace.append(k)
                if r and k.endswith(prefix):
                    to_replace.append(k)
    for el in to_replace:
        data.pop(el, None)

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
        data_dict['source'] = 'vk'
        if data_dict.get('user', None) is None:
            data_dict['user'] = {'sn_id': data_dict.pop('from_id', None) or data_dict.get('uid', None)}
        if not 'sn_id' in data_dict:
            data_dict['sn_id'] = data_dict.pop('cid', None) or data_dict.pop('id', None)
        data_dict['created_at'] = datetime.datetime.fromtimestamp(int(data_dict.pop('date')))
        if comment_for:
            data_dict['comment_for'] = comment_for
            data_dict['comment_id'] = comment_id or data_dict['comment_id']
        data_dict['user_id'] = data_dict['user']['sn_id']

        data_dict.pop('cid', None)
        data_dict.pop('online', None)
        data_dict.pop('uid', None)
        _process_text_fields(data_dict)
        super(VK_APIMessage, self).__init__(data_dict)

    @property
    def comment_id(self):
        return self.get('comment_id')


class VK_APIContentObject(APIContentObject):
    def __init__(self, data_dict):
        data_dict['source'] = 'vk'
        _process_text_fields(data_dict)
        super(VK_APIContentObject, self).__init__(data_dict)


class VK_APISocialObject(APISocialObject):
    def __init__(self, data_dict):
        data_dict['sn_id'] = data_dict.get('id')
        _delete_fields_with_prefix(data_dict,('is_','photo_'), l=True, r=False)
        super(VK_APISocialObject, self).__init__(data_dict)



class ContentResult(object):
    def __init__(self):
        self._content = []
        self._relations = []
        self._comments = []

    def __add_object(self, object_type, object_acc, object):
        if isinstance(object, list):
            object_acc.extend(object)
        elif isinstance(object, object_type):
            object_acc.append(object)

    def add_relations(self, relation_objects):
        self.__add_object(tuple, self.relations, relation_objects)

    def add_comments(self, comments):
        self.__add_object(APIMessage, self.comments, comments)

    def add_content(self, content_objects):
        self.__add_object(APIContentObject, self.content, content_objects)

    def get_content_to_persist(self):
        return chain(self.comments, self.content)

    @property
    def content(self):
        return self._content

    @property
    def relations(self):
        return self._relations

    @property
    def comments(self):
        return self._comments

    @relations.setter
    def relations(self, value):
        self._relations = value

    @content.setter
    def content(self, value):
        self._content = value

    @comments.setter
    def comments(self, value):
        self._comments = value

    def get_relations_with_type(self, relation_type, l=True, r=True):
        if not isinstance(relation_type, (list,tuple,set)):
            relation_type = [relation_type]
        returned_rels = [(el[0],el[2]) for el in self.relations if (el[1] in relation_type)]
        if not l:
            returned_rels = [el[0] for el in returned_rels]
        elif not r:
            returned_rels = [el[1] for el in returned_rels]
        return returned_rels

    def __radd__(self, other):
        if isinstance(other, self.__class__):
            self.comments += other.comments
            self.content += other.content
            self.relations += other.relations
            return self
        else:
            raise ValueError("+ operator with not ContentResult object")

    def __iadd__(self, other):
        return self.__radd__(other)

    def __add__(self, other):
        return self.__radd__(other)


def _take_by(lst, by=1):
    for i in xrange((len(lst) / by) + 1):
        yield ",".join([str(el) for el in lst[i * by: (i + 1) * by]])


if __name__ == '__main__':
    d = {'is_admin':1, 'is_hui':1, 'tototo':1, 'foo':3, 'bar':3, 'baba':1}
    _delete_fields_with_prefix(d, ('is_', 'ba'), True,True)
    print d
