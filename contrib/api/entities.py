# coding=utf-8
from datetime import datetime
import logging
from bson import DBRef
from contrib.api.proxy import ProxyHandler

from requests import Session, ConnectionError


__author__ = '4ikist'

log = logging.getLogger('API')


class ProxySession(Session):
    def __init__(self, reinit_callback, check_callback):
        super(ProxySession, self).__init__()
        self.proxy_handler = ProxyHandler()
        self._reinit_proxies()
        self._reinit_callback = reinit_callback
        self._check_callback = check_callback

    def _reinit_proxies(self):
        self.proxies = {'https': "https://%s" % self.proxy_handler.get_next()}

    def get(self, url, **kwargs):
        while True:
            try:
                result = super(ProxySession, self).get(url, **kwargs)
                if not self._check_callback(result):
                    self._reinit_proxies()
                    self._reinit_callback()
                    continue
                else:
                    return result
            except ConnectionError as e:
                log.exception(e)
                self._reinit_proxies()


    def post(self, url, **kwargs):
        while True:
            result = super(ProxySession, self).post(url, **kwargs)
            if not self._check_callback(result):
                self._reinit_callback()
                self._reinit_proxies()
                continue
            else:
                return result


def delete_fields_with_prefix(data, prefixes, l=True, r=False):
    to_replace = []
    if isinstance(prefixes, (str,unicode)):
        prefixes = [prefixes]

    for k, v in data.iteritems():
        if isinstance(k, (str, unicode)):
            for prefix in prefixes:
                if l and k.startswith(prefix):
                    to_replace.append(k)
                if r and k.endswith(prefix):
                    to_replace.append(k)
    for el in to_replace:
        data.pop(el, None)


class API(object):
    pass

class APIRequestOverflowException(Exception):
    pass


class APIException(Exception):
    pass

class APIResponseException(Exception):
    pass


class APIContentObject(dict):
    """
    Сущность хранящая в себе некоторый контент (фотография, заметка, видео)
    """
    def __init__(self, data_dict):
        super(APIContentObject, self).__init__(data_dict)

    def __hash__(self):
        return self.get('sn_id')

    @property
    def sn_id(self):
        return self.get('sn_id')

    @property
    def update_date(self):
        return self.get('update_date')



class APISocialObject(APIContentObject):
    '''
    Сущность хранящая в себе некоторый социальнй объект (группа, страница, прочее)
    '''
    def __init__(self, data_dict):
        super(APISocialObject, self).__init__(data_dict)

    @property
    def members(self):
        return self.get('members')


class APIUser(APIContentObject):
    def __init__(self, data_dict):
        super(APIUser, self).__init__(data_dict)

    @property
    def name(self):
        return self.get('name')

    @property
    def screen_name(self):
        return self.get('screen_name')

    @property
    def messages_count(self):
        return self.get('statuses_count')

    @property
    def friends_count(self):
        return self.get('friends_count')

    @property
    def followers_count(self):
        return self.get('followers_count')


class APIMessage(APIContentObject):
    def __init__(self, data_dict):
        super(APIMessage, self).__init__(data_dict)

    @property
    def user_id(self):
        user = self.get('user')
        if user:
            if isinstance(user, dict):
                return self.get('user').get('sn_id')
            else:
                return self.get('user_id')
        raise AttributeError('in any message you must have user owner!')

    @property
    def text(self):
        return self.get('text')