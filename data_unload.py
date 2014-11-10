# coding=utf-8
import argparse
from collections import Counter

from contrib.db.database_engine import Persistent
from contrib.api.vk.vk_entities import rel_types_user

__author__ = '4ikist'
__doc__ = """
Скрипт для выгрузки анных социального графа в csv/
Выгружается следующим образом два файла с узлами и ребрами. Файл с узлами отражает пользователей и их данные. С ребрами - их взаимовсвязи/
Фомат файла с узлами: идентификатор_пользователя_в_сс:screen_name:friend_count:followers_count:statuses_count:created_at
формат файла с ребрами: идентификатор_от_кого:идентификатор_к_кому:тип_связи:количество (если vk и определенные типы связей)
"""
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-fn', '--file_name', type=str,
                        help='template of filename and will form: <your_template>_nodes.csv and <your_template>_relations.csv')
    parser.add_argument('-s', '--source', help='retrieve only for special social net, now it can be ttr or vk')

    parser.add_argument('-mh', '--mongo_host', help='host of mongodb')
    parser.add_argument('-mp', '--mongo_port', help='port of mongodb')
    parser.add_argument('-mdn', '--mongo_database_name', help='database name of mongodb')
    parser.add_argument('-rh', '--redis_host', help='host of redis')
    parser.add_argument('-rp', '--redis_port', help='port of redis')
    parser.add_argument('-rdn', '--redis_database_number', help='number of database in redis', type=int, default=0)

    args = parser.parse_args()
    nodes_f = open('%snodes.csv' % ('%s_' % (args.file_name or '')), 'w')
    nodes_f.write('Id;Label;Friends_count;Followers_count;Statuses_count\n')
    relations_f = open('%srelations.csv' % ('%s_' % (args.file_name or '')), 'w')
    relations_f.write('Source;Target;Type')
    persist = Persistent(False, args.mongo_host, args.mongo_port, args.mongo_database_name,
                         args.redis_host,
                         args.redis_port,
                         args.redis_database_number)
    query = {}
    if args.source:
        query['source'] = args.source

    users_iterator = persist.get_users_iter(query)
    for user in users_iterator:
        str = '%(sn_id)s;%(screen_name)s;%(friends_count)s;%(followers_count)s;%(statuses_count)s\n' % user
        print str
        nodes_f.write(str)
        related = {}
        for rel_type in rel_types_user:
            for related_id in persist.get_related_from(user.sn_id, rel_type):
                str_rel = '%s;%s;%s\n' % (user.sn_id, related_id, rel_type)
                print str_rel
                relations_f.write(str_rel)

    nodes_f.close()
    relations_f.close()


