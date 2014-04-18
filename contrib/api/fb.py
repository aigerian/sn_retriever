from contrib.db.mongo_db_connector import db_handler

__author__ = '4ikist'

from facebook import GraphAPI, GraphAPIError

from contrib.api.entities import API
from properties import *

import logging

import urlparse

from lxml import html
import requests


class FB_API(API):
    """
    facebook api implement
    """

    def __init__(self):
        self.log = logging.getLogger("FB_API")
        access_token = self.__auth().get('access_token')
        self.log.info('Auth. Access_token: %s' % (access_token))
        self.graph = GraphAPI(access_token)

        self.search_types = ['post', 'user', 'page', 'event', 'group']
        self.user_data_fields = ["tagged", "feed", "links", "notes", "posts", "statuses"]
        self.user_relations_fields = ["mutualfriends", "friends", "subsribers", "subscribedto", "family"]
        self.user_relations_group_fields = ["groups", "events", "likes"]

        try:
            self.db_data = db_handler().create_temp_collection('fb')
        except Exception as e:
            self.log.warn(e)

    def __auth(self):
        s = requests.Session()
        s.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0',
                     'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                     'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
                     'Accept-Encoding': 'gzip, deflate'}

        s.verify = certs_path
        params = {'client_id': fb_app_id, 'redirect_uri': 'https://www.facebook.com/connect/login_success.html'}
        #https://www.facebook.com/dialog/oauth?client_id=182482928555387&redirect_uri=https://www.facebook.com/connect/login_success.html
        login_result = s.get('https://www.facebook.com/dialog/oauth', params=params)
        doc = html.document_fromstring(login_result.content)
        inputs = doc.xpath('//input')
        form_params = {}
        for el in inputs:
            form_params[el.attrib.get('name')] = el.value
        form_params['email'] = fb_user_email
        form_params['pass'] = fb_user_pass
        s.headers['Referer'] = login_result.url

        auth_url = doc.xpath('//form')[0].attrib.get('action')
        auth_result = s.post('https://www.facebook.com/%s' % auth_url, data=form_params)
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
        retrieving data using function with paging

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

        # self.db_data.save(result_buff)
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

        #retrieving user info
        dirty_result = {}
        for field in self.user_data_fields + self.user_relations_fields:
            field_result = self._retrieve_with_paging(user_id, self.graph.get_connections, **{'connection_name': field})
            if len(field_result):
                dirty_result[field] = field_result

        #clearing posting result
        dirty_result['posting_data'] = {}
        posting_result = []
        data_ids = set()
        for field in self.user_data_fields:
            data = dirty_result.pop(field, None)
            if not data:
                continue
            for el in data:
                if el['id'] not in data_ids:
                    data_ids.add(el['id'])
                    posting_result.append(el)
                else:
                    self.log.debug('%s this %s in data ids...' % (el, field))
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
        for field in self.user_relations_fields:
            data = dirty_result.pop(field, None)
            if not data:
                continue
            dirty_result['relations_data'][field] = data


        #forming relations group data
        dirty_result["relations_groups_data"] = {}
        for field in self.user_relations_group_fields:
            field_result = self._retrieve_with_paging(user_id, self.graph.get_connections, **{'connection_name': field})
            if len(field_result):
                if field == 'likes':
                    dirty_result["relations_groups_data"]['pages'] = field_result
                else:
                    dirty_result["relations_groups_data"][field] = field_result

        return dirty_result

    def user_group_info(self, group_id, group_type):
        """
        group_type can be: [group, page, event]
        :return: {
            object: group object info,
            relations:{id: {'relations':[admin,member]}}
            posting_relations:{[id, count_likes, comments]}
        }
        """
        result = {}
        text_data = {}
        if group_type == 'group':
            try:
                members_result = self._retrieve_with_paging(group_id, self.graph.get_connections,
                                                            **{'connection_name': 'members'})
                for el in members_result:
                    if el['administrator'] == 'true':
                        result[el['id']] = {'relations': ['admin']}
                    else:
                        result[el['id']] = {'relations': ['member']}

                # self.db_data.save(members_result)
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

                # self.db_data.save(result)
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
            # self.db_data.save(result)

        feed_result = self._retrieve_with_paging(group_id, self.graph.get_connections, **{'connection_name': 'feed'})
        users_from_feed = self._retrieve_relations_from_post_data(feed_result)
        if group_type == 'page':
            users_from_feed = FB_API._sum_posts_relations_results(result, users_from_feed)
            result = None

        object = self.graph.get_object(group_id)

        return {'relations': result, 'posting_relations': users_from_feed, 'object': object}

    def search(self, q, search_type=None):
        result = {}
        q = unicode(q).encode('utf-8')
        if not search_type:
            for s_type in self.search_types:
                s_result = self._retrieve_with_paging('search', self.graph.get_object, **{'q': q, 'type': s_type})
                result[s_type] = s_result
        else:
            result[search_type] = self._retrieve_with_paging('search', self.graph.get_object,
                                                             **{'q': q, 'type': search_type})

        return result

if __name__ == '__main__':
    api = FB_API()
    result = api.user_group_info('195466193802264','group')
    print result
