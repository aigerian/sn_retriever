# coding:utf-8
import sys
from contrib.api.ttr import TTR_API
from contrib.db.database_engine import Persistent
from contrib.utils import SocialDataStreamer
from properties import logger
import properties

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

log = logger.getChild('walker_ttr')


def get_user_relations(user_sn_id, relation_type, persist, ttr):
    related_ids, next_cursor = ttr.get_relation_ids(user_sn_id, relation_type)
    while next_cursor not in (0, -1):
        if isinstance(related_ids, list):
            next_batch, next_cursor = ttr.get_relation_ids(user_sn_id, relation_type, from_cursor=next_cursor)
            related_ids.extend(next_batch)
    saved = persist.get_related_from(user_sn_id, relation_type)
    persist.save_relation(user_sn_id, list(set(related_ids).difference(saved)), relation_type)
    # visualise
    return related_ids


def persist_messages(user_data, persist, ttr):
    log.info('start loading timeline for user %s' % user_data.screen_name)
    last_message = persist.get_message_last(user_data)
    request = {'user': user_data}
    if last_message:
        request['since_id'] = last_message.sn_id
        log.info('we have messages for %s, last saved %s' % (user_data.screen_name, last_message['update_date']))
    user_messages = ttr.get_all_timeline(**request)
    count_saved = 0
    for message in user_messages:
        persist.save_message(message)
        count_saved += 1
    log.info('loaded: %s messages' % count_saved)


def persist_all_user_data_and_retrieve_related_ids(screen_name, relation_type, persist, ttr):
    def form_user(screen_name):
        log.info('start loading user: %s' % screen_name)
        query = {}
        if isinstance(screen_name, int) or screen_name.isdigit():
            query['sn_id'] = screen_name
        else:
            query['screen_name'] = screen_name
        saved = persist.get_user(**query)
        if not saved:
            user = ttr.get_user(**query)
            persist.save_user(user)
        else:
            user = saved
            log.info('we have user %s (was load at %s)' % (user.screen_name, user.update_date))
        # visualise
        return user

    user = form_user(screen_name)
    if user is None:
        log.error('can not load %s :(' % screen_name)
        return []

    persist_messages(user, persist, ttr)
    log.info('start loading %s of %s' % (relation_type, user.screen_name))
    related_ids = get_user_relations(user.sn_id, relation_type, persist, ttr)
    log.info('loaded %s related ids' % len(related_ids))
    return related_ids


def persist_users_by_ids_and_retrieve_friends(ids, relation_type, persist, ttr):
    result = []
    loaded, _ = ttr.get_users(filter(lambda x: persist.is_not_loaded(x), ids))
    if len(_):
        log.error('we have not loaded ids:\n%s' % ', '.join(_))
    for user_data in set(loaded):
        log.info('loaded user %s' % user_data.screen_name)
        persist.save_user(user_data)
        persist_messages(user_data, persist, ttr)
        result.extend(get_user_relations(user_data, relation_type, persist, ttr))
    return result


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--list', type=file, help='load list of user ids you must provide file of this list')
    parser.add_argument('-u', '--user', help='load one user name')
    parser.add_argument('-rt', '--relation_type',
                        help='using specific relation type, as default using \'friends\', you can use \'followers\'', )
    parser.add_argument('-d', '--depth', type=int,
                        help='depth of social (friends and followers) and saving users relations', )
    parser.add_argument('-v', '--visualise', help='will sending to gephi data', action='store_true')

    parser.add_argument('-tr', '--truncate_db', help='will truncate database !WARNING', action='store_true')
    parser.add_argument('-mh', '--mongo_host', help='host of mongodb')
    parser.add_argument('-mp', '--mongo_port', help='port of mongodb')
    parser.add_argument('-mdn', '--mongo_database_name', help='database name of mongodb')
    parser.add_argument('-rh', '--redis_host', help='host of redis')
    parser.add_argument('-rp', '--redis_port', help='port of redis')
    parser.add_argument('-rdn', '--redis_database_number', help='number of database in redis', type=int, default=0)

    args = parser.parse_args()
    if args.list:
        with args.list as f:
            users = [el.strip() for el in f.xreadlines()]
    else:
        users = [args.user] if args.user else []

    relation_type = args.relation_type or relation_type
    depth = args.depth or 1

    ttr = TTR_API()
    if args.visualise:
        persist = SocialDataStreamer(args.mongo_host, args.mongo_port, args.mongo_database_name, args.redis_host, args.redis_port,
                                     args.redis_database_number)
    else:
        persist = Persistent(args.truncate_db, args.mongo_host, args.mongo_port, args.mongo_database_name, args.redis_host,
                             args.redis_port,
                             args.redis_database_number)

    log.info(
        '\n-----------\n'
        'start load from this users: \n'
        '%s \n\n'
        'with relation type: %s\n'
        'with depth: %s\n\n'
        ''
        'data save to: %s\n'
        'relations save to: %s\n'
        '-------------' % (
            '\n'.join(users), relation_type, depth, persist.mongo_uri,
            '%s:%s[%s]' % (args.redis_host or properties.redis_host,
                           args.redis_port or properties.redis_port,
                           args.redis_database_number or 0)))

    loaded_users = []
    for _ in range(args.depth or 1):
        related_users = []
        for user in users:
            related_users.extend(persist_all_user_data_and_retrieve_related_ids(user, relation_type, persist, ttr))
            loaded_users.append(user)
        users = list(set(related_users).difference(loaded_users))


