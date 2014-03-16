import random
import threading
from datetime import datetime, timedelta
import time
from birdy.twitter import UserClient, BirdyException, TwitterApiError
from contrib.api.proxy import ProxyHandler
from contrib.db.mongo_db_connector import db_handler
import properties

max_apps_count = len(properties.ttr_access_tokens) + 1
log = properties.logger.getChild('TTR')

wait_times = {'api/followers/ids': 3600 / 14,
              'api/friends/ids': 3600 / 14,
              'api/users/show': 3600 / 175,
              'api/statuses/user_timeline': 3600 / 290,
              'api/search/tweets':3600/440}


class LimitHandler(object):
    def __init__(self):
        self.requests_types = {}

    def _get_first(self, list_of_dates):
        biggest_delta = None
        best_key = None
        for k, v in list_of_dates.iteritems():
            if v is None:
                biggest_delta, best_key = timedelta(seconds=999), k
                break
            current_delta = datetime.now() - v
            if not biggest_delta or not best_key:
                biggest_delta, best_key = current_delta, k
            else:
                if biggest_delta < current_delta:
                    biggest_delta, best_key = current_delta, k

        return best_key, biggest_delta.seconds

    def get_credentials_number(self, request_name):
        if self.requests_types.get(request_name):
            credential_number, seconds = self._get_first(self.requests_types[request_name])
        else:
            self.requests_types[request_name] = dict([(el, None) for el in range(1, max_apps_count)])
            credential_number, seconds = random.randint(1, max_apps_count - 1), 999

        wait_seconds = wait_times[request_name] - seconds
        log.debug('best credentials is %i and will wait %i\ncredentials times:\n%s' % (
            credential_number,
            wait_seconds if wait_seconds > 0 else 0,
            '\n'.join(
                ["%i : %s%s" % (k, v.strftime('[%H:%M:%S]') if v else None, '<-' if k == credential_number else '') for
                 k, v in
                 self.requests_types[request_name].iteritems()])))

        return credential_number, wait_seconds if wait_seconds > 0 else 0

    def consider_credentials_number(self, request_name, credential_number, request_time):
        if self.requests_types.get(request_name):
            self.requests_types[request_name][credential_number] = request_time
        else:
            self.requests_types[request_name] = dict(
                [(el, None if el != credential_number else request_time) for el in range(1, max_apps_count)])


class TTR_API(object):
    work_end = 'work_end'

    def __init__(self):
        self.credential_number = 1
        self.proxy_handler = ProxyHandler()
        self.client = UserClient(None, None)
        self.limit_handler = LimitHandler()

    def __get_client_params(self, use_proxy):
        client_params = properties.get_ttr_credentials(self.credential_number)
        if use_proxy:
            client_params['proxies'] = self.proxy_handler.get_next()
        return client_params

    def __get_request_name(self, function):
        return function.im_self._path

    def __ensure_sn_id(self, sn_object):
        result = dict(sn_object)
        result['sn_id'] = result.pop(u'id')
        return result

    def _form_new_client(self, credential_number, use_proxy=False):
        self.credential_number = credential_number
        self.client = UserClient(**self.__get_client_params(use_proxy))
        return self.client

    def __get_data(self, callback, **kwargs):
        request_name = self.__get_request_name(callback)
        use_proxy = False
        while True:
            try:
                cred_number, wait_time = self.limit_handler.get_credentials_number(request_name)
                callback.im_self._client = self._form_new_client(cred_number, use_proxy)
                time.sleep(wait_time)
                request_time = datetime.now()
                response = callback(**kwargs)
                return response
            except TwitterApiError as e:
                log.exception(e)
                return None
            except BirdyException as e:
                log.info('problem with: %s and request name: %s' % (kwargs, request_name))
                log.exception(e)
                use_proxy = True
            except Exception as e:
                log.exception(e)
            finally:
                self.limit_handler.consider_credentials_number(request_name, cred_number, request_time)

    def get_all_relations(self, user, relation_type='friends', from_cursor=-1):
        cursor = from_cursor
        while True:
            response = self.__get_data(self.client.api[relation_type].ids.get,
                                       screen_name=user['screen_name'],
                                       count=200,
                                       cursor=cursor)
            if response:
                cursor = response.data.next_cursor
                yield response.data.ids, cursor
                if not cursor:
                    break
            else:
                break

    def get_user(self, **kwargs):
        response = self.__get_data(self.client.api.users.show.get, **kwargs)
        if response:
            return self.__ensure_sn_id(response.data)
        else:
            return None

    def get_all_timeline(self, user, max_id=None):
        max_id = max_id
        while True:
            response = self.__get_data(self.client.api.statuses.user_timeline.get,
                                       screen_name=user['screen_name'],
                                       count=200,
                                       trim_user=True,
                                       include_rts=True,
                                       max_id=max_id)
            if response:
                if max_id:
                    yield [self.__ensure_sn_id(el) for el in response.data[1:]], max_id
                else:
                    yield [self.__ensure_sn_id(el) for el in response.data], max_id
                if len(response.data) != 200:
                    break
                else:
                    max_id = response.data[-1][u'id']
            else:
                break

    def search(self, q, until=None, result_type='recent', lang='ru', geocode=None, max_id=None, count_iterations=10):
        max_id = max_id
        iteration = 0
        while iteration <= count_iterations:
            iteration+=1
            params = {'q': q,
                      'result_type': result_type,
                      'lang': lang,
                      'count': 100,
                      'include_entities':True
            }
            if geocode:
                params['geocode'] = geocode
            if until and isinstance(until, datetime):
                params['until'] = until.strftime("%Y-%m-%d")
            if max_id:
                params['max_id'] = max_id
            response = self.__get_data(self.client.api.search.tweets.get, **params)
            if response:
                max_id = response.data.statuses[-1][u'id']
                yield response.data.statuses, max_id
                if len(response.data.statuses) < 99:
                    break
            else:
                break


if __name__ == '__main__':
    api = TTR_API()
    db = db_handler()
    medvedev = api.get_user(screen_name='medvedevRussia')
    duty = db.get_duty({'work': 'medvedev_get_follwers'})
    if duty:
        cursor = duty['cursor']
    else:
        cursor = -1
        #friends_mdv = api.get_all_relations(medvedev, from_cursor=cursor)

    followers_mdv = api.get_all_relations(medvedev, relation_type='followers')

    def found_user(user_ids, api, db):
        for user_ids_batch, cursor in user_ids:
            for user_id in user_ids_batch:
                user = api.get_user(user_id=str(user_id))
                if user:
                    db.save_user(user)
            db.save_duty({'work': 'medvedev_get_followers', 'cursor': cursor}, 'medvedev_get_followers')


    t_follwers = threading.Thread(target=found_user, kwargs={'user_ids': followers_mdv, 'api': api, 'db': db})
    t_follwers.start()
    t_follwers.join()