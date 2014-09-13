# coding=utf-8
from contrib.db.database_engine import Persistent

__author__ = '4ikist'

__doc__ = """Обновляет пользователей уже сохраненных и прописывыает всем у кого не задан source равным ttr """

if __name__ == '__main__':
    persist = Persistent()
    counter = 0
    for user in persist.get_users_iter():
        if 'source' not in user:
            counter += 1
            user['source'] = 'ttr'
        persist.save_user(user)
    print "updated %s users" % counter
