from contrib.api.ttr import __TTR_API
from contrib.core.characteristics import TTR_Characterisitcs
from contrib.core.latane.functions import LataneFunctions
from contrib.db.database_engine import GraphPersistent, Persistent

__author__ = '4ikist'


if __name__ == '__main__':
    api = __TTR_API()
    characteristics = TTR_Characterisitcs(Persistent(), api)
    graph_persistence = GraphPersistent(truncate=True)
    latane = LataneFunctions(characteristics, graph_persistence)

    me = api.get_user(screen_name='linoleum2k12')
    me_id = graph_persistence.save_user(me)
    for el in api.get_relations(me, 'friends'):
        friend_id = graph_persistence.save_user(el)
        graph_persistence.save_relations(me_id, friend_id, {'type':'friend'})

    for el in api.get_relations(me, 'followers'):
        follower_id = graph_persistence.save_user(el)
        graph_persistence.save_relations(me_id,follower_id, {'type':'follower'})

    lat_res = latane.execute(me)
    print lat_res