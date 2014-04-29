from datetime import datetime
import logging
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

#TODO refactor!
class API(object):
    def __auth(self):
        pass

    def get(self, method_name, **kwargs):
        pass

    def get_relations(self, user_id, relation_type='friends'):
        pass

    def search(self, q):
        pass


class APIRequestOverflowException(Exception):
    pass


class APIException(Exception):
    pass


class APISocialObject(dict):
    def __init__(self, data_dict, created_at_format=None, from_db=False):
        data = dict(data_dict)
        if not from_db:
            data['sn_id'] = data.pop('id')
            data['created_at'] = datetime.strptime(data['created_at'],
                                                   created_at_format if created_at_format else '%a %b %d %H:%M:%S +0000 %Y')
        super(APISocialObject, self).__init__(data)

    def __hash__(self):
        return self.get('sn_id')


class APIUser(APISocialObject):
    def __init__(self, data_dict, created_at_format=None, from_db=False):
        super(APIUser, self).__init__(data_dict, created_at_format, from_db)

    @property
    def name(self):
        return self.get('name')

    @property
    def screen_name(self):
        return self.get('screen_name')

    @property
    def sn_id(self):
        return self.get('sn_id')

    @property
    def messages_count(self):
        return self.get('statuses_count')

    @property
    def friends_count(self):
        return self.get('friends_count')

    @property
    def followers_count(self):
        return self.get('followers_count')


class APIMessage(APISocialObject):
    def __init__(self, data_dict, created_at_format=None, from_db=False):
        data = dict(data_dict)
        if not from_db:
            retweet = data.get('retweeted_status')
            if retweet:
                retweet = dict(retweet)
                rt_user = dict(retweet.get('user'))
                rt_user = {'sn_id': rt_user.get('id')}
                retweet['user'] = rt_user
                data['retweeted_status'] = retweet
            user = {'sn_id': data['user']['id']}
            data['user'] = user
        super(APIMessage, self).__init__(data, created_at_format, from_db)

