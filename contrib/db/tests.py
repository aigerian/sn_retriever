from contrib.db.database_engine import RedisGraphPersistent
import random
from contrib.db.utils import unload_graph

__author__ = '4ikist'

def shortest_path_redis():
    rgp = unload_graph('test')
    prev_node = None
    for el in rgp.nodes_iter():
        if prev_node and 'linoleum' in el.get('name'):
            rgp.get_shortest_path(el.get('name'), prev_node)
            prev_node = el
        elif 'medvedev' in el.get('name'):
            prev_node = el

if __name__ == '__main__':
    shortest_path_redis()