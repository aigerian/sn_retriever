import random
from datetime import datetime, timedelta
import time
from birdy.twitter import UserClient, BirdyException, TwitterApiError, TwitterClientError
from contrib.api.entities import APIUser, APIMessage
from contrib.api.proxy import ProxyHandler
import properties

max_apps_count = len(properties.ttr_access_tokens) + 1
log = properties.logger.getChild('TTR')

wait_times = {'api/followers/ids': 3600 / 14,
              'api/followers/list': 3600 / 14,

              'api/friends/ids': 3600 / 14,
              'api/friends/list': 3600 / 14,

              'api/friendships/show': 3600 / 14,

              'api/users/show': 3600 / 175,
              'api/users/lookup': 3600 / 55,

              'api/statuses/user_timeline': 3600 / 290,
              'api/statuses/retweets': 3600 / 440,
              'api/statuses/show': 3600 / 440,

              'api/search/tweets': 3600 / 440,
}

ttr_datetime_format = '%a %b %d %H:%M:%S +0000 %Y'


class TTRLimitHandler(object):
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
            self.requests_types[request_name] = dict([(el, None) for el in xrange(1, max_apps_count)])
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
                [(el, None if el != credential_number else request_time) for el in xrange(1, max_apps_count)])


class __TTR_API(object):
    work_end = 'work_end'

    def __init__(self):
        self.credential_number = 1
        self.proxy_handler = ProxyHandler()
        self.client = UserClient(None, None)
        self.limit_handler = TTRLimitHandler()

    def __get_client_params(self, use_proxy):
        client_params = properties.get_ttr_credentials(self.credential_number)
        if use_proxy:
            client_params['proxies'] = self.proxy_handler.get_next()
        return client_params

    def __get_request_name(self, function):
        return function.im_self._path

    def _form_message(self, message_data):
        return APIMessage(message_data)

    def _form_user(self, user_data):
        return APIUser(user_data)

    def _form_new_client(self, credential_number, use_proxy=False):
        self.credential_number = credential_number
        self.client = UserClient(**self.__get_client_params(use_proxy))
        return self.client

    def __get_data(self, callback, **kwargs):
        request_name = self.__get_request_name(callback)
        use_proxy = False
        while True:
            cred_number, wait_time = self.limit_handler.get_credentials_number(request_name)
            try:
                log.debug('send_request:  %s %s [%s]' % (request_name, str(kwargs), wait_time))
                callback.im_self._client = self._form_new_client(cred_number, use_proxy)
                time.sleep(wait_time)
                request_time = datetime.now()
                response = callback(**kwargs)
                return response
            except TwitterApiError as e:
                log.exception(e)
                return None
            except TwitterClientError as e:
                log.error('may be internet is closed? %s' % e)
                return None
            except BirdyException as e:
                log.info('problem with: %s and request name: %s' % (kwargs, request_name))
                log.exception(e)
                use_proxy = True
            except Exception as e:
                log.exception(e)
            except MemoryError as e:
                log.exception(e)
            finally:
                self.limit_handler.consider_credentials_number(request_name, cred_number, request_time)

    def get_relation_ids(self, user, relation_type='friends', from_cursor=-1):
        response = self.__get_data(self.client.api[relation_type].ids.get,
                                   user_id=user.get('sn_id'),
                                   count=5000,
                                   cursor=from_cursor)
        if response:
            return response.data.ids, response.data.next_cursor

    def get_relations(self, user, relation_type='friends', from_cursor=-1):
        cursor = from_cursor
        while True:
            response = self.__get_data(self.client.api[relation_type].list.get,
                                       user_id=user['sn_id'],
                                       count=200,
                                       cursor=cursor,
                                       skip_status=False,
                                       include_entites=True)
            if response:
                cursor = response.data.next_cursor
                for el in response.data.users:
                    yield self._form_user(el)
                if not cursor:
                    break
            else:
                break

    def get_friendship_data(self, user_one, user_two):
        params = {}
        if isinstance(user_one, str):
            params['source_screen_name'] = user_one
        elif isinstance(user_one, dict):
            params['source_screen_name'] = user_one.get('screen_name')
            params['source_id'] = user_one.get('sn_id')
        elif isinstance(user_one, (int, long)):
            params['source_id'] = user_one

        if isinstance(user_two, str):
            params['target_screen_name'] = user_two
        elif isinstance(user_two, dict):
            params['target_screen_name'] = user_two.get('screen_name')
            params['target_id'] = user_two.get('sn_id')
        elif isinstance(user_two, (int, long)):
            params['target_id'] = user_two

        response = self.__get_data(self.client.api.friendships.show.get, **params)
        if response:
            result = {'one_to_two': False, 'two_to_one': False}
            if response.data.relationship.source.followed_by:
                result['one_to_two'] = True
            if response.data.relationship.target.followed_by:
                result['two_to_one'] = True
            return result

    def get_user(self, **kwargs):
        response = self.__get_data(self.client.api.users.show.get, **kwargs)
        if response:
            return self._form_user(response.data)
        else:
            return None

    def get_users(self, ids=None, screen_names=None):
        def fill_data(request_params):
            response = self.__get_data(self.client.api.users.lookup.get, **request_params)
            if response:
                for user in response.data:
                    result_ids.add(user.get('sn_id'))
                    result.append(self._form_user(user))

        result = []
        result_ids = set()
        request_params = {}
        if ids:
            for i in xrange((len(ids) / 100) + 1):
                request_params['user_id'] = ",".join([str(el) for el in ids[i * 100:(i + 1) * 100]])
                fill_data(request_params)

        if screen_names:
            for i in xrange((len(screen_names) / 100) + 1):
                request_params['screen_name'] = ",".join([str(el) for el in screen_names[i * 100:(i + 1) * 100]])
                fill_data(request_params)

        log.info("must load: %s; loaded: %s" % (
            len(ids) if ids else 0 + len(screen_names) if screen_names else 0, len(result)))
        not_loaded = result_ids.symmetric_difference(result_ids)
        return result, not_loaded


    def get_message(self, message_id):
        """
        :param message_id: id of message in ttr
        :return: message and user
        """
        params = {'id': message_id, 'trim_user': False, 'include_entities': True, 'include_my_retweet': False}
        response = self.__get_data(self.client.api.statuses.show.get, **params)
        user = response.data.user
        if response.data:
            return self._form_message(response.data), self._form_user(user)


    def get_all_timeline(self, user, max_id=None, since_id=None):
        """
        return generator of batches of user timeline and max id
        :param user: user which timeline you want to retrieve (some)
        :param max_id: timeline before this id
        :param since_id: timeline after this id
        :return: generator of tweets
        """
        max_id = max_id
        while True:
            response = self.__get_data(self.client.api.statuses.user_timeline.get,
                                       screen_name=user['screen_name'],
                                       count=200,
                                       trim_user=True,
                                       include_rts=True,
                                       max_id=max_id,
                                       since_id=since_id)
            if response:
                for el in response.data:
                    yield self._form_message(el)

                if len(response.data) != 200:
                    break
                else:
                    max_id = response.data[-1][u'id']
            else:
                break

    def search(self, q, until=None, result_type='recent', lang='ru', geocode=None, max_id=None, count_iterations=10,
               batch_count=10):
        iteration = 0
        while iteration <= count_iterations:
            iteration += 1
            params = {'q': q,
                      'result_type': result_type,
                      'lang': lang,
                      'count': 100,
                      'include_entities': True
            }
            if geocode:
                params['geocode'] = geocode
            if until and isinstance(until, datetime):
                params['until'] = until.strftime("%Y-%m-%d")
            if max_id:
                params['max_id'] = max_id
            response = self.__get_data(self.client.api.search.tweets.get, **params)
            if response and len(response.data.statuses):
                max_id = response.data.statuses[-1][u'id']
                if batch_count:
                    for i in range(len(response.data.statuses), step=batch_count):
                        yield [self._form_message(el) for el in i] #forelini%))))))
                else:
                    for el in response.data.statuses:
                        yield self._form_message(el)

                if len(response.data.statuses) < 99:
                    break
            else:
                break


    def get_retweets(self, tweet_id):
        params = {'id': tweet_id, 'trim_user': True, 'include_entities': True, 'count': 100}
        response = self.__get_data(self.client.api.statuses.retweets.get, **params)
        retweets = response.data
        for el in retweets:
            yield self._form_message(el)


api = __TTR_API()


def get_api(api_name='ttr'):
    if not api_name or api_name =='ttr':
        return api


if __name__ == '__main__':
    # api = TTR_API()
    # db = db_handler()
    # medvedev = api.get_user(screen_name='medvedevRussia')
    # duty = db.get_duty({'work': 'medvedev_get_follwers'})
    # if duty:
    #     cursor = duty['cursor']
    # else:
    #     cursor = -1
    #     #friends_mdv = api.get_all_relations(medvedev, from_cursor=cursor)
    #
    # followers_mdv = api.get_all_relations(medvedev, relation_type='followers')
    #
    # def found_user(user_ids, api, db):
    #     for user_ids_batch, cursor in user_ids:
    #         for user_id in user_ids_batch:
    #             user = api.get_user(user_id=str(user_id))
    #             if user:
    #                 db.save_user(user)
    #         db.save_duty({'work': 'medvedev_get_followers', 'cursor': cursor}, 'medvedev_get_followers')
    #
    #
    # t_follwers = threading.Thread(target=found_user, kwargs={'user_ids': followers_mdv, 'api': api, 'db': db})
    # t_follwers.start()
    # t_follwers.join()

    # user1 = api.get_user(screen_name='@linoleum2k12')
    # user2 = api.get_user(screen_name='@lutakisel4ikova')
    # rel_date = api.get_friendship_data(user1,user2)

    api = __TTR_API()
    # medved = api.get_user(screen_name = 'linoleum2k12')
    # followers,cursor = api.get_relation_ids(medved,relation_type='followers')
    result = api.get_all_timeline({'screen_name': 'linoleum2k12'})
    for el in result:
        print el