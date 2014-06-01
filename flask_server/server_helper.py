from time import sleep
from contrib.api.threading.api_threads import ThreadHandler
from contrib.api.ttr import get_api
from contrib.core.characteristics import TTR_Characterisitcs
from contrib.core.latane.functions import LataneFunctions
from contrib.core.social_net_graph import TTR_Graph
from contrib.db.database_engine import Persistent

__author__ = '4ikist'

not_ended = 'not_ended'


class ServerHelper(object):
    def __init__(self, persistent, api):
        self.api = api
        self.persistent = persistent
        self.characteristics = TTR_Characterisitcs(persistent, api)
        self.social_net_graph = TTR_Graph(persistent, api)
        self.latane = LataneFunctions(self.characteristics, self.social_net_graph)

        self.th = ThreadHandler()
        self.waited = {}

    def form_user(self, screen_name):
        def ensure_user_extended_info(user):
            mentions = self.characteristics.mentions(user)
            hashtags = self.characteristics.hashtags(user)
            urls = self.characteristics.urls(user)
            messages = self.persistent.get_messages({'user.$id': user.get('_id')})
            rt_count = 0
            for el in messages:
                rt_count += el.get('retweet_count')
            latane_function_result = self.latane.execute(user)
            latane_function_with_ht_result = self.latane.execute(user, include_hash_tags=True)
            latane_function_with_urls_result = self.latane.execute(user, include_urls=True)
            latane_function_with_ht_and_urls_result = self.latane.execute(user, include_urls=True,
                                                                          include_hash_tags=True)
            return {'mentions': mentions,
                    'hashtags': hashtags,
                    'urls': urls,
                    'retweets_count': rt_count,
                    'latane': latane_function_result,
                    'latane_ht': latane_function_with_ht_result,
                    'latane_urls': latane_function_with_urls_result,
                    'latane_ht_urls': latane_function_with_ht_and_urls_result}

        user = self.persistent.get_user(screen_name=screen_name)
        if user:
            extended_info = self.persistent.get_extended_user_info(user.get('_id'))
            if extended_info:
                return {'user': user, 'extended_info': extended_info}
            else:
                wait_for_extended_info = self.th.call(ensure_user_extended_info, user=user)
                self.waited[wait_for_extended_info] = {'screen_name': screen_name}
                return {'wait': wait_for_extended_info}
        else:
            wait_user = self.th.call(ensure_user_extended_info, user=screen_name)
            self.waited[wait_user] = {'screen_name': screen_name}
            return {'wait': wait_user}

    def get_user_result(self, wait_identity):
        if not self.th.is_ready(wait_identity):
            return not_ended
        result = self.th.get_result(wait_identity)
        wait_info = self.waited.get(wait_identity)
        user = self.persistent.get_user(screen_name=wait_info.get('screen_name'))
        self.persistent.save_extended_user_info(user_id=user.get('_id'), extended_info=result)
        del self.waited[wait_identity]
        return {'user': user, 'extended_info': result}


    def retrieve_search_result(self, query):
        result_gen = self.api.search(q=query)

        def retrieve_result(gen):
            result = []
            for el in gen:
                result.append(el)
            return result

        identity = self.th.call(retrieve_result, gen=result_gen)
        return identity

    def get_search_result(self, identity):
        if self.th.is_ready(identity):
            return self.th.get_result(identity)
        return not_ended


if __name__ == '__main__':
    sh = ServerHelper(Persistent(), get_api())
    identity = sh.form_user('@linoleum2k12')
    user_result = None
    if identity.get('user') and identity.get('extended_info'):
        print identity
    else:
        while True:
            wait_identity = identity.get('extended_info_wait')
            result = sh.get_user_result(wait_identity)
            if not result:
                print 'wait....'
                sleep(1)
            else:
                print result
                break