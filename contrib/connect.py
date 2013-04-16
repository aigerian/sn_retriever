import json

__author__ = '4ikist'

import requests
import base64

from properties import *
from loggers import get_logger

log = get_logger('connect')


class ApiConnection(object):
    def __init__(self):
        self.basic_url = 'https://api.twitter.com'
        token = self.__auth()
        if token:
            self.bearer_token = token

    def __auth(self):
        log.info('processing auth')
        issue_key = base64.standard_b64encode('%s:%s' % (consumer_key, consumer_secret))
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

    def get(self, command, **kwargs):
        log.info('GET %s' % command)
        headers = {'Authorization': 'Bearer %s' % self.bearer_token}
        result = requests.get('%s/1.1/%s.json' % (self.basic_url, command), headers=headers, params=kwargs)
        log.debug('>> %s \nheaders:\t%s' % (result.request.url, result.request.headers))
        log.debug('<< [%s] %s' % (result.status_code, result.text))
        try:
            result = json.loads(result.content)
            return result
        except ValueError as e:
            log.error('result have not contain json object')


if __name__ == '__main__':
    api = ApiConnection()
    result = api.get('statuses/user_timeline', **{'screen_name': 'linoleum2k12'})
    result = api.get('friends/ids', **{'screen_name': 'linoleum2k12'})
    result = api.get('followers/ids', **{'screen_name': 'linoleum2k12'})
