__author__ = '4ikist'
from contrib.db.database_engine import Persistent

if __name__ == '__main__':
    p = Persistent()
    p.start_listen_deferred_objects()