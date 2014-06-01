from time import sleep
from contrib.api.threading.api_threads import ThreadHandler
from contrib.api.ttr import get_api
from contrib.core.characteristics import TTR_Characterisitcs
from contrib.core.latane.functions import LataneFunctions
from contrib.core.social_net_graph import TTR_Graph
from contrib.db.database_engine import Persistent
from contrib.utils import process_message

__author__ = '4ikist'


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
            return {'mentions': mentions, 'hashtags': hashtags, 'urls': urls, 'retweets_count': rt_count}

        user = self.persistent.get_user(screen_name=screen_name)
        if user:
            extended_info = self.persistent.get_extended_user_info(user.get('_id'))
            if extended_info:
                return {'user': user, 'extended_info': extended_info}
            else:
                wait_for_extended_info = self.th.call(self.latane.execute, user=user)
                self.waited[wait_for_extended_info] = {'wait': 'extended_info'}
                return {'user': user, 'extended_info_wait': wait_for_extended_info}
        else:
            wait_user = self.th.call(self.latane.execute, user=screen_name)
            self.waited[wait_user] = {'wait': ['extended_info', 'user'], 'screen_name': screen_name}
            return {'user_wait': wait_user, 'extended_info_wait': wait_user}

    def get_user_result(self, wait_identity):
        wait_info = self.waited.get(wait_identity)
        if wait_info:
            if self.th.is_ready(wait_identity):
                result = self.th.get_result(wait_identity)
                if isinstance(wait_info.get('wait'), list):
                    user = self.persistent.get_user(screen_name=wait_info.get('screen_name'))
                    self.persistent.save_extended_user_info(user.get('_id'), {'latane_function': result})
                    del self.waited[wait_identity]
                    return {'user': user, 'extended_info': {'latane_function': result}}
                elif isinstance(wait_info.get('wait'), str):
                    del self.waited[wait_identity]
                    return {'extended_info': {'latane_function': result}}
            else:
                return None
        else:
            return None

    def retrieve_result(gen):
        result = []
        for el in gen:
            result.append(el)
        return result

    def retrieve_search_result(self, query, **s_params):
        result_gen = self.api.search(q=query, **s_params)
        identity = self.th.call(self.retrieve_result, gen=result_gen)
        return identity

    class ttr_photo_retriever(object):
        def __init__(self, api='ttr'):
            self.persist = Persistent()
            self.api = get_api(api)

            self.main_obj = ServerHelper(persistent=self.persist, api=api)

        def load_batch(self, query, lang='ru'):
            identity = self.main_obj.retrieve_search_result(query, lang='ru', batch_count=100, count_iterations=100)
            search_result = None
            while True:
                search_result = self.main_obj.get_search_result(identity)
                if search_result:
                    break
                else:
                    sleep(1)
            urls = []
            for el in search_result:
                message_entites = process_message(el.get('content'))
                for me in message_entites:
                    if me['type'] == 'url':
                        urls.append(me['content'])
            for el in urls:
                print el

            return urls


    def get_search_result(self, identity):
        if self.th.is_ready(identity):
            return self.th.get_result(identity)
        return None


if __name__ == '__main__':
    ServerHelper.ttr_photo_retriever().load_batch()