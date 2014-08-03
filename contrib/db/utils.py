from contrib.db.database_engine import RedisGraphPersistent, Persistent

__author__ = '4ikist'

def unload_graph(name):
    rgp = RedisGraphPersistent(name)
    persistent = Persistent()

    for el in persistent.get_users_iter():
        el['name'] = el['screen_name']
        rgp.save_node(el)
        for rel in persistent.get_related_users(el.sn_id,'friends'):
            rgp.save_ref(el['name'],rel.sn_id, 'friends', {})

        for rel in persistent.get_related_users(el.sn_id,'followers'):
            rgp.save_ref(el['name'],rel.sn_id, 'followers', {})

    return rgp