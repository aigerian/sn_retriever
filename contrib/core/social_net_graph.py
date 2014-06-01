from datetime import datetime
from functools import partial

import networkx as nx
from networkx import NetworkXNoPath

from contrib.api.entities import APIUser
from contrib.api.ttr import get_api
from contrib.core.tracking import TTR_Tracking
from contrib.db.database_engine import Persistent
import properties

__author__ = '4ikist'


class API_Exception(Exception):
    pass


class TTR_Graph(nx.DiGraph):
    def __init__(self, persistent, api=None):
        self.persistent = persistent
        self.api = api
        if api:
            self.tracker = TTR_Tracking(self.api, self.persistent)

        super(TTR_Graph, self).__init__()

    def get_related_iterator(self, rel_type, n):
        if not self.api:
            for el in self._get_persist_rels_sn_ids(n, rel_type):
                yield el

        update_date = self.persistent.get_relations_update_time(n, rel_type)
        if not update_date:
            cursor = -1
            while cursor != 0:
                result = self.api.get_relation_ids({'sn_id': n}, relation_type=rel_type, from_cursor=cursor)
                if not result:
                    break
                related_ids, cursor = result
                not_loaded_users = []
                for user_id in related_ids:
                    if self.persistent.is_not_loaded(user_id):
                        not_loaded_users.append(user_id)
                loaded, not_loaded = self.api.get_users(ids=not_loaded_users)
                for loaded_user in loaded:
                    self.persistent.save_user(loaded_user)
                del loaded
                for el in related_ids:
                    if el in not_loaded:
                        continue
                    self.persistent.save_relation(from_id=n, to_id=el, relation_type=rel_type)
                    yield el
        else:
            if (datetime.now() - update_date).total_seconds() > properties.relation_cache_time:
                updated_n = self.api.get_user(user_id=n)
                if updated_n is None:
                    yield None
                real_refs_count = self.persistent.get_relations_count(n, rel_type)
                delta = updated_n.get('%s_count' % rel_type) - real_refs_count
                if delta != 0:
                    new, remove, acc = self.tracker.get_relations_diff(updated_n, delta, rel_type)
                    for el in new:
                        if self.persistent.is_not_loaded(el):
                            loaded_user = self.api.get_user(user_id=el)
                            if not loaded_user:
                                self.persistent.remove_relation(n, rel_type, el)
                            else:
                                self.persistent.save_user(loaded_user)
                    for el in acc:
                        yield el
                else:
                    for el in self._get_persist_rels_sn_ids(n, rel_type):
                        yield el
            else:
                for el in self._get_persist_rels_sn_ids(n, rel_type):
                    yield el

    def _get_persist_rels_sn_ids(self, from_id, rel_type):
        users_sn_ids = self.persistent.get_related_users(from_id=from_id, relation_type=rel_type, only_sn_ids=True)
        for el in users_sn_ids:
            yield el

    def predecessors_iter(self, n):
        return partial(self.get_related_iterator, 'friends')(n)

    def successors_iter(self, n):
        return partial(self.get_related_iterator, 'followers')(n)

    def __get_user_node(self, screen_name):
        if isinstance(screen_name, APIUser):
            return screen_name
        result = self.persistent.get_user(screen_name=screen_name)
        if not result:
            if self.api:
                result = self.api.get_user(screen_name=screen_name)
                if not result:
                    raise nx.NetworkXNoPath("TTR have not this user [%s]" % screen_name)
                self.persistent.save_user(result)
            else:
                raise nx.NetworkXNoPath("I have not this user [%s]" % screen_name)
        return result

    def shortest_path(self, from_screen_name, to_screen_name):
        f, t = self.__get_user_node(from_screen_name), self.__get_user_node(to_screen_name)
        try:

            result = nx.shortest_path(self, f.get('sn_id'), t.get('sn_id'))
            self.persistent.save_path(result)
            return result
        except NetworkXNoPath as e:
            return None


    def shortest_path_length(self, from_screen_name, to_screen_name):
        """
        return length between two nodes
         if no path between - return -1
        """
        result = self.shortest_path(from_screen_name, to_screen_name)
        if result:
            return len(result)
        return -1


if __name__ == '__main__':
    api = get_api()
    persistent = Persistent()
    g = TTR_Graph(persistent, api)
    result = g.shortest_path('@medvedevRussia', '@linoleum2k12')
    for el in result:
        print persistent.get_user(sn_id=el).screen_name

