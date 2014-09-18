# coding:utf-8
import sys
from contrib.api.ttr import TTR_API
from contrib.db.database_engine import Persistent
from properties import logger

__author__ = '4ikist'
__doc__ = """
Скрипт для выкачки пользователей социальных сетей.
Алгоритм работы:
1) Выкачивает данные о пользователе со стартовым именем (start_user_screen_name), а также все его сообщения.
2) Формирует список его связей (тип связи указан в переменной relation_type)
3) Идя по этому списку для каждого идентификатора пользователя делает пп. 1,2.
"""

relation_type = 'friends'
start_user_screen_name = 'linoleum2k12'


ttr = TTR_API()
persist = Persistent()

log = logger.getChild('walker_ttr')

def get_user_relations(user_data, relation_type):
    log.info('start loading user relations (%s) for user %s'%(relation_type, user_data.screen_name))
    friends_ids, next_cursor = ttr.get_relation_ids(user_data, relation_type)
    while next_cursor not in (0,-1):
        if isinstance(friends_ids, list):
            next_batch, next_cursor = ttr.get_relation_ids(user_data, relation_type, from_cursor=next_cursor)
            friends_ids.extend(next_batch)
    for el in set(friends_ids):
        persist.save_relation(user_data.sn_id, el, relation_type)
    return friends_ids


def persist_messages(user_data):
    log.info('start loading timeline for user %s' % user_data.screen_name)
    user_messages = ttr.get_all_timeline(user_data)
    for message in user_messages:
        persist.save_message(message)


def persist_all_user_data_and_retrieve_friends_ids(screen_name, relation_type):
    log.info('start loading user: %s'%screen_name)
    user = ttr.get_user(screen_name=screen_name)
    persist.save_user(user)
    persist_messages(user)
    return get_user_relations(user, relation_type)


def persist_users_by_ids_and_retrieve_friends(ids, relation_type):
    result = []
    loaded, _ = ttr.get_users(ids)
    if len(_):
        log.error('we have not loaded ids:\n%s'%', '.join(_))
    for user_data in set(loaded):
        log.info('loaded user %s'%user_data.screen_name)
        persist.save_user(user_data)
        persist_messages(user_data)
        result.extend(get_user_relations(user_data, relation_type))
    return result


if __name__ == '__main__':
    if len(sys.argv) == 3:
        start_user_screen_name = sys.argv[1]
        relation_type = sys.argv[2]
    elif len(sys.argv) == 2:
        start_user_screen_name = sys.argv[1]
        relation_type = 'friends'
    else:
        print '''
        usage: python walker_ttr.py <start_user_name> [<relation_type>] where
        start_user_name - some user name which will start walk from
        relation_type - can be [friends, followers], friends as default
        '''
        sys.exit(-2)

    related_users_ids = persist_all_user_data_and_retrieve_friends_ids(start_user_screen_name, relation_type)
    while 1:
        related_users_ids = persist_users_by_ids_and_retrieve_friends(related_users_ids, relation_type)

