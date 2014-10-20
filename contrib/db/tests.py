from contrib.db.database_engine import RedisGraphPersistent, RedisBaseMixin
import random
from contrib.db.utils import unload_graph
from contrib.timers import stopwatch

__author__ = '4ikist'

def shortest_path_redis():
    rgp = unload_graph('test.html')
    prev_node = None
    for el in rgp.nodes_iter():
        if prev_node and 'linoleum' in el.get('name'):
            rgp.get_shortest_path(el.get('name'), prev_node)
            prev_node = el
        elif 'medvedev' in el.get('name'):
            prev_node = el

@stopwatch
def test_redis_relations():
    db_rel = RedisBaseMixin(truncate=True, db_num=10)
    count = 2
    @stopwatch
    def test_save_multi():
        db_rel.save_relations('1',range(count),'test_multi')

    @stopwatch
    def test_save():
        for i in xrange(count):
            db_rel.save_relations('1',i,'test')

    test_save_multi()
    test_save()
    print db_rel.get_count('1','test')
    print db_rel.get_count('1','test_multi')

    print db_rel.get_relations('1','test')
    assert db_rel.get_count('1','test') == count
    assert db_rel.get_count('1','test_multi') == count


if __name__ == '__main__':
    test_redis_relations()