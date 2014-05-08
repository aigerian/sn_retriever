from contrib.db.database_engine import GraphPersistent
import random

__author__ = '4ikist'


def __get_ne(user, from_users):
    res = random.choice(from_users)
    if res == user:
        res = __get_ne(user, from_users)
    return res


def ensure_new_db():
    db = GraphPersistent(True)

    users = []
    for i in range(100):
        user_id = db.save_user({'sn_id': i, 'screen_name': 'foo_bar_%s' % i})
        users.append(user_id)
        if len(users) > 2:
            from_ = random.choice(users)
            to_ = __get_ne(from_, users)
            db.save_relations(from_, to_, {'type': 'friends'})

    return db


if __name__ == '__main__':
    #db = ensure_new_db()
    db = GraphPersistent()
    id_0 = db.save_user({'screen_name': 'foo_bar_102', 'sn_id': 102})
    id_1 = db.save_user({'screen_name': 'foo_bar_103', 'sn_id': 103})
    user_not_in_graph_db = db.get_user(screen_name='foo_bar_100')
    saved_node = db.graph_db.get_node(str(id_0))
    not_saved_node = db.graph_db.get_node(str(user_not_in_graph_db.get('_id')))
    path_length = db.get_path_length(str(id_1), id_0, 'friends')
    print path_length