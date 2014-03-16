import functools
import time
import logging
from contrib.api.proxy import ProxyHandler

import properties
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