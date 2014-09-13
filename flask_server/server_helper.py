from time import sleep
from contrib.api.threading.api_threads import ThreadHandler
from contrib.api.ttr import get_api
from contrib.core.characteristics import TTR_Characterisitcs
from contrib.core.latane.functions import LataneFunctions
from contrib.core.social_net_graph import TTR_Graph
from contrib.db.database_engine import Persistent
from contrib.utils import process_message

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
        self.search_gens = {}

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

        user = self.persistent.get_user_info(screen_name=screen_name)
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
        user = self.persistent.get_user_info(screen_name=wait_info.get('screen_name'))
        self.persistent.save_extended_user_info(user_id=user.get('_id'), extended_info=result)
        del self.waited[wait_identity]
        return {'user': user, 'extended_info': result}

    def is_ready(self, identity):
        return self.th.is_ready(identity)

    def __retrieve_result(gen=[]):
        result = []
        for el in gen:
            result.append(el)
        return result

    def retrieve_search_result(self, query=None, gen_identity=None, **s_params):
        if gen_identity:
            result_gen = self.search_gens[gen_identity]
        elif query:
            result_gen = self.api.search(q=query, **s_params)
        else:
            return None
        try:
            identity = self.th.call(result_gen.next)
            self.search_gens[identity] = result_gen
            return identity
        except Exception:
            return None

    class ttr_photo_retriever(object):
        def __init__(self, api='ttr'):
            self.persist = Persistent()
            self.api = get_api(api)
            self.retr_objects = {}
            self.main_obj = ServerHelper(persistent=self.persist, api=api)

        def start_search(self, query, lang='ru'):
            identity = self.main_obj.retrieve_search_result(query, lang='ru', batch_count=100, count_iterations=100)
            return identity


        def is_ready(self, identity):
            if identity in self.retr_objects[identity]:
                return self.retr_objects[identity]
            search_result = self.main_obj.get_search_result(identity)
            if search_result is not None:
                self.retr_objects[identity] = search_result
                return search_result
            return False

        def get_search_result(self, identity):
            ready_result = self.is_ready(identity)
            if not ready_result:
                return None

            urls = []
            for el in ready_result:
                message_entites = process_message(el.get('content'))
                for me in message_entites:
                    if me['type'] == 'url':
                        urls.append(me['content'])
            for el in urls:
                print el
            return urls


    def get_search_result(self, identity):
        if self.th.is_ready(identity):
            return self.th.get_result(identity), self.retrieve_search_result(gen_identity=identity)
        return None


if __name__ == '__main__':
    pass

