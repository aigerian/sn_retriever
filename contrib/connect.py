#coding: utf-8
__author__ = '4ikist'

import json
import base64
import logging
import urlparse

from hashlib import sha1
import hmac
import binascii

from lxml import html
import requests

from properties import *
import re

from facebook import GraphAPI, GraphAPIError

log = logging.getLogger('API')


class API(object):
    def __auth(self):
        pass

    def get(self, method_name, **kwargs):
        pass

    def get_relations(self, user_id, relation_type='friends'):
        pass

    def search(self, q):
        pass


class FB_API(API):
    """
    facebook api implement
    """

    def __init__(self):
        access_token = self.__auth().get('access_token')
        self.graph = GraphAPI(access_token)
        self.log = logging.getLogger("FB_API")

    def __auth(self):
        s = requests.Session()
        params = {'client_id': fb_app_id, 'redirect_uri': 'https://www.facebook.com/connect/login_success.html'}
        login_result = s.get('https://www.facebook.com/dialog/oauth', params=params)
        doc = html.document_fromstring(login_result.content)
        inputs = doc.xpath('//input')
        form_params = {}
        for el in inputs:
            form_params[el.attrib.get('name')] = el.value
        form_params['email'] = fb_user_email
        form_params['pass'] = fb_user_pass

        auth_result = s.post('https://www.facebook.com/login.php', data=form_params)
        assert 'Success' in auth_result.content

        parse = urlparse.urlparse(auth_result.url)
        confirm_params = {'client_id': fb_app_id, 'redirect_uri': params['redirect_uri'],
                          'client_secret': fb_app_secret, 'code': parse.query[5:]}

        result = s.get('https://graph.facebook.com/oauth/access_token', params=confirm_params)

        access_params = dict([el.split('=') for el in result.content.split('&')])
        return access_params

    @staticmethod
    def _get_paging_params(url):
        parsed = urlparse.urlparse(url)
        param_until = urlparse.parse_qs(parsed.query).get('until')
        param_after = urlparse.parse_qs(parsed.query).get('after')
        token = urlparse.parse_qs(parsed.query).get('__paging_token')
        result = {}
        if token:
            result['__paging_token'] = token[0]
        if param_until:
            result['until'] = param_until[0]
        elif param_after:
            result['after'] = param_after[0]
        return result or None

    @staticmethod
    def _create_relation(buffer, object_id, relation_name):
        if buffer.has_key(object_id):
            buffer[object_id]['relations'].append(relation_name)
        else:
            buffer[object_id] = {'relations': [relation_name]}
        return buffer

    @staticmethod
    def _create_relations(buffer, relations_data, relation_name):
        for el in relations_data:
            result = FB_API._create_relation(buffer, el['id'], relation_name)
            buffer.update(result)
        return buffer

    @staticmethod
    def _sum_posts_relations_results(result_one, result_two):
        all_keys = set(result_one.keys() + result_two.keys())
        result = {}
        for key in all_keys:
            val_one = result_one.get(key)
            val_two = result_two.get(key)
            if not val_one:
                val = val_two
            elif not val_two:
                val = val_one
            else:
                if 'likes' in val_one and 'likes' in val_two:
                    likes_count = val_one['likes'] + val_two['likes']
                else:
                    likes_count = val_one.get('likes') or val_two.get('likes') or 0

                if 'comments' in val_one and 'comments' in val_two:
                    comments = val_one['comments']
                    comments.extend(val_two['comments'])
                else:
                    comments = val_one.get('comments') or val_two.get('comments') or None
                val = {}
                if likes_count != 0:
                    val['likes'] = likes_count
                if comments:
                    val['comments'] = comments

            result[key] = val
        return result

    @staticmethod
    def _add_like(posting_data, id):
        if posting_data.has_key(id):
            if posting_data[id].has_key('likes'):
                posting_data[id]['likes'] += 1
            else:
                posting_data[id]['likes'] = 1
        else:
            posting_data[id] = {'likes': 1}

    @staticmethod
    def _add_comment(posting_data, id, comment_message):
        if posting_data.has_key(id):
            if posting_data[id].has_key('comments'):
                posting_data[id]['comments'].append(comment_message)
            else:
                posting_data[id]['comments'] = [comment_message]
        else:
            posting_data[id] = {'comments': [comment_message]}

    def _retrieve_with_paging(self, object_id, function, **kwargs):
        """
        retrieving data use function with paging

        :param: field_name
        :return: [] with data or empty
        """
        result_buff = []
        try:
            self.log.info('retrieving with paging used: %s\nand args: %s' % (function, kwargs))
            fb_connections_data = function(object_id, **kwargs)
            result_buff += fb_connections_data.get(u'data')
            paging = fb_connections_data.get(u'paging')
            while paging:
                next = paging.get('next')
                if not next:
                    break
                paging_params = FB_API._get_paging_params(next)
                if not paging_params:
                    break
                else:
                    paging_params['limit'] = 25
                self.log.info('paging: %s' % (paging_params))
                kwargs.update(paging_params)
                fb_appended_data = function(object_id, **kwargs)
                result_buff += fb_appended_data.get(u'data')
                paging = fb_appended_data.get(u'paging')
        except GraphAPIError as e:
            self.log.error(e)

        return result_buff


    def _retrieve_relations_from_post_data(self, posting_data, exclude_id=None):
        """
        interested: likes, comments
        :return: {id}
        """
        posting_relations = {}
        for posting_element in posting_data:
            likes = posting_element.get(u'likes')
            if likes:
                if likes['paging'].has_key('next'):
                    likes_data = self._retrieve_with_paging(posting_element.get(u'id'), self.graph.get_connections,
                                                            **{'connection_name': 'likes'})
                else:
                    likes_data = likes.get('data')
                for like_el in likes_data:
                    if like_el['id'] == exclude_id:
                        continue
                    FB_API._add_like(posting_relations, like_el['id'])

            comments = posting_element.get(u'comments')
            if comments:
                if comments['paging'].has_key('next'):
                    comments_data = self._retrieve_with_paging(posting_element.get(u'id'), self.graph.get_connections,
                                                               **{'connection_name': 'comments'})
                else:
                    comments_data = comments.get('data')

                for comment_el in comments_data:
                    if comment_el['from']['id'] == exclude_id:
                        continue
                    FB_API._add_comment(posting_relations, comment_el['from']['id'], comment_el['message'])

        return posting_relations

    def get_user_extended_info(self, user_id):
        """
        :param: user_id - id of user
        :return: {
            posting_data:{tagged:[],feed:[]...},
            posting_relations_data:[id:{likes:count_likes, comments:[comments data],...}],
            relations_data:{mutualfriends:[], friends:[], ...},
            relations_groups_data:{groups:[], events:[], pages:[]},
            user:user_object
        }
        note: in relations_data likes is page which user is liked
        """
        user_data_fields = ["tagged", "feed", "links", "notes", "posts", "statuses"]
        user_relations_fields = ["mutualfriends", "friends", "subsribers", "subscribedto", "family"]
        user_relations_group_fields = ["groups", "events", "likes"]
        #retrieving user info
        dirty_result = {}
        for field in user_data_fields + user_relations_fields:
            field_result = self._retrieve_with_paging(user_id, self.graph.get_connections, **{'connection_name': field})
            if len(field_result):
                dirty_result[field] = field_result

        #clearing posting result
        dirty_result['posting_data'] = {}
        posting_result = []
        data_ids = set()
        for field in user_data_fields:
            data = dirty_result.pop(field, None)
            if not data:
                continue
            for el in data:
                if el['id'] not in data_ids:
                    data_ids.add(el['id'])
                    posting_result.append(el)
                else:
                    self.log('%s this %s in data ids...' % (el, field))
                dirty_result['posting_data'][field] = el


        #forming relations from posting data
        posting_relations_data = self._retrieve_relations_from_post_data(posting_result, user_id)
        dirty_result['posting_relations_data'] = posting_relations_data

        #retrieving user object
        try:
            fields = 'id, name, first_name, middle_name, last_name, gender, locale, languages, link, username, age_range, updated_time, education, email, hometown, interested_in, location, political, quotes, relationship_status, religion, website, work'
            object = self.graph.get_object(user_id, fields=fields)
            dirty_result['user'] = object
        except GraphAPIError as e:
            self.log.error(e)

        #forming relations data
        dirty_result['relations_data'] = {}
        for field in user_relations_fields:
            data = dirty_result.pop(field, None)
            if not data:
                continue
            dirty_result['relations_data'][field] = data


        #forming relations group data
        dirty_result["relations_groups_data"] = {}
        for field in user_relations_group_fields:
            field_result = self._retrieve_with_paging(user_id, self.graph.get_connections, **{'connection_name': field})
            if len(field_result):
                if field == 'likes':
                    dirty_result["relations_groups_data"]['pages'] = field_result
                else:
                    dirty_result["relations_groups_data"][field] = field_result

        return dirty_result

    def user_group_info(self, group_id, group_type):
        """
        group type can be: [group, page, event]
        :return: {
            object: group object info,

        }
        """
        result = {}
        if group_type == 'group':
            try:
                members_result = self._retrieve_with_paging(group_id, self.graph.get_connections,
                                                            **{'connection_name': 'members'})
                for el in members_result:
                    if el['administrator'] == 'true':
                        result[el['id']] = {'relations': ['admin']}
                    else:
                        result[el['id']] = {'relations': ['member']}
            except GraphAPIError as e:
                self.log.error(e)

        if group_type == 'event':
            try:
                noreply = self._retrieve_with_paging(group_id, self.graph.get_connections,
                                                     **{'connection_name': 'noreply'})
                result = FB_API._create_relations(result, noreply, 'noreply')

                invited = self._retrieve_with_paging(group_id, self.graph.get_connections,
                                                     **{'connection_name': 'invited'})
                result = FB_API._create_relations(result, invited, 'invited')

                attending = self._retrieve_with_paging(group_id, self.graph.get_connections,
                                                       **{'connection_name': 'attending'})
                result = FB_API._create_relations(result, attending, 'attending')

                maybe = self._retrieve_with_paging(group_id, self.graph.get_connections, **{'connection_name': 'maybe'})
                result = FB_API._create_relations(result, maybe, 'maybe')

                declined = self._retrieve_with_paging(group_id, self.graph.get_connections,
                                                      **{'connection_name': 'declined'})
                result = FB_API._create_relations(result, declined, 'declined')

            except GraphAPIError as e:
                self.log.error(e)

        if group_type == 'page':
            posts = self._retrieve_with_paging(group_id, self.graph.get_connections, **{'connection_name': 'posts'})
            tagged = self._retrieve_with_paging(group_id, self.graph.get_connections, **{'connection_name': 'tagged'})
            promotable_posts = self._retrieve_with_paging(group_id, self.graph.get_connections,
                                                          **{'connection_name': 'promotable_posts'})
            statuses = self._retrieve_with_paging(group_id, self.graph.get_connections,
                                                  **{'connection_name': 'statuses'})
            data_ids = set()
            page_posts_result = []
            for el in posts + tagged + promotable_posts + statuses:
                if el['id'] not in data_ids:
                    data_ids.add(el['id'])
                    page_posts_result.append(el)

            result = self._retrieve_relations_from_post_data(page_posts_result)

        feed_result = self._retrieve_with_paging(group_id, self.graph.get_connections, **{'connection_name': 'feed'})
        users_from_feed = self._retrieve_relations_from_post_data(feed_result)
        if group_type == 'page':
            users_from_feed = FB_API._sum_posts_relations_results(result, users_from_feed)
            result = None

        object = self.graph.get_object(group_id)

        return {'relations': result, 'posting_relations': users_from_feed, 'object': object}


    def search(self, query):
        search_types = ['post', 'user', 'page', 'event', 'group']
        result = {}

        for s_type in search_types:
            s_result = self._retrieve_with_paging('search', self.graph.get_object)
            result[s_type] = s_result

        return result


class VkAPIException(Exception):
    def __init__(self, params):
        self.message = str(params)
        self.args = params


class VK_API(API):
    def __init__(self):
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
        log.info('vkontakte authenticate')
        result = requests.get('https://oauth.vk.com/authorize', params=vk_access_credentials)
        doc = html.document_fromstring(result.content)
        inputs = doc.xpath('//input')
        form_params = {}
        for el in inputs:
            form_params[el.attrib.get('name')] = el.value
        form_params['email'] = vk_login
        form_params['pass'] = vk_pass
        form_url = doc.xpath('//form')[0].attrib.get('action')
        #process second page
        result = requests.post(form_url, form_params, cookies=result.cookies)
        doc = html.document_fromstring(result.content)
        #if already login
        if 'OAuth Blank' not in doc.xpath('//title')[0].text:
            submit_url = doc.xpath('//form')[0].attrib.get('action')
            result = requests.post(submit_url, cookies=result.cookies)

        #retrieving access token from url
        parsed_url = urlparse.urlparse(result.url)
        if 'error' in parsed_url.query:
            log.error('error in authenticate \n%s' % parsed_url.query)
            raise VkAPIException(dict([el.split('=') for el in parsed_url.query.split('&')]))

        fragment = parsed_url.fragment
        access_token = dict([el.split('=') for el in fragment.split('&')])
        log.info('get access token: \n%s' % access_token)
        return access_token

    def get(self, method_name, **kwargs):
        params = dict({'access_token': self.access_token['access_token']}, **kwargs)
        result = requests.get('%s%s' % (self.base_url, method_name), params=params)
        result_object = json.loads(result.content)
        if 'error' in result_object:
            raise VkAPIException(result_object)
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
        command = 'wall.get'
        kwargs = {'owner_id': user_id, 'filter': 'all', }
        result = self.get_all(command,
                              batch_size=100,
                              items_process=self.array_item_process,
                              count_process=self.array_count_process,
                              **kwargs)
        return result

    def get_notes(self, user_id):
        command = 'notes.get'
        kwargs = {'user_id': user_id, 'sort': 1}
        result = self.get_all(command,
                              batch_size=100,
                              items_process=self.array_item_process,
                              count_process=self.array_count_process,
                              **kwargs)
        return result

    def get_post_comments(self, post_id, owner_id):
        """
        :param post_id: the identification of post from wall of user who have -
        :param owner_id: this id
        :return: array of comments with who, when and text information
        """
        command = 'wall.getComments'
        kwargs = {'owner_id': owner_id, 'post_id': post_id, 'need_likes': 1, 'sort': 'asc', 'preview_length': '0'}
        result = self.get_all(command,
                              batch_size=100,
                              items_process=self.array_item_process,
                              count_process=self.array_count_process,
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
        return result

    def search(self, q):
        """
        :param q:
        :return:
        """
        command = 'newsfeed.search'
        kwargs = {'extended': 1, 'q': q, 'count': 1000}
        result = self.get(command, **kwargs)
        return result[1:]


class Ttr_API(API):
    def __init__(self):
        self.basic_url = 'https://api.twitter.com'
        token = self.__auth()
        if token:
            self.bearer_token = token

    def __auth(self):
        log.info('processing auth')
        issue_key = base64.standard_b64encode('%s:%s' % (ttr_consumer_key, ttr_consumer_secret))
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
            except APIOutException as e:
                break
        return all

    def _get_cursored(self, cursored_first_result, list_name, command, **kwargs):
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

    def get_user(self, user_id=None, screen_name=None):
        """
        return user representation
        :param user_id:
        :param screen_name:
        :return:
        """
        kwargs = {'user_id': user_id, 'screen_name': screen_name}
        command = "users/show"
        result = self.get(command, **kwargs)
        return result

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
        if not user_id and not screen_name:
            raise APIInException('specify user id or screen name')
        if relation_type not in ('friends', 'followers'):
            raise APIInException('specify valid relation type')

        kwargs = {'user_id': user_id, 'screen_name': screen_name, 'count': 5000, 'cursor': -1}
        command = '%s/ids' % relation_type

        first_result = self.get(command, **kwargs)
        full_result = self._get_cursored(first_result, 'ids', command, **kwargs)
        return full_result

    def search(self, q):
        params = {'count': 100, 'q': q}
        command = 'search/tweets'
        tweet_result = self.get(command, **params).get('statuses')
        return tweet_result


class APIOutException(Exception): pass


class APIInException(Exception): pass
