# coding=utf-8
from contrib.timers import stopwatch
from neo4jrestclient.utils import text_type

__author__ = '4ikist'

import logging

#from py2neo import neo4j, node
from neo4jrestclient.client import GraphDatabase
from contrib.db import DataBase
import properties

#temp imports

rt_say = 'SAY'
rt_comes = 'COMES'

log = logging.getLogger('gdb')


class Neo4j_handler(DataBase):
    @staticmethod
    def create_relation_index(f, t, rtype):
        return '_'.join([str(f), str(t), str(rtype)])

    def __init__(self, truncated=False):
        self.db = GraphDatabase(properties.gdb_host)
        if truncated:
            self.db.query(q=""" MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r """)

        self.index_users = self.db.nodes.indexes.create('users')
        self.index_words = self.db.nodes.indexes.create('words')

        self.index_relations_users = self.db.relationships.indexes.create('words_relations')
        self.index_relations_words = self.db.relationships.indexes.create('users_relations')
        self.index_relations_hybrid = self.db.relationships.indexes.create('hybrid_relations')


    def get_user(self, user_id):
        result_list = self.index_users.get('sn_id', user_id)
        if len(result_list):
            return result_list[0]
        return None

    def save_relation(self, from_, to_, relation_type='friend', relation_data={}):
        rel = self.db.relationships.create(from_, relation_type, to_)
        if isinstance(relation_data, dict):
            for k, v in relation_data.iteritems():
                rel[k] = v
        if relation_type == rt_comes:
            self.index_relations_words.add('wr',
                                           Neo4j_handler.create_relation_index(from_._id, to_._id, relation_type),
                                           rel)
        elif relation_type in ['friend', 'follower']:
            self.index_relations_users.add('ur',
                                           Neo4j_handler.create_relation_index(from_._id, to_._id, relation_type),
                                           rel)
        elif relation_type == rt_say:
            self.index_relations_hybrid.add('hr',
                                            Neo4j_handler.create_relation_index(from_._id, to_._id, relation_type),
                                            rel)
        return rel

    def get_relation_data(self, from_, to_, relation_type):
        rel_index = Neo4j_handler.create_relation_index(from_._id, to_._id, relation_type)
        if relation_type == rt_say:
            res_list = self.index_relations_hybrid.get('hr', rel_index)
        elif relation_type == rt_comes:
            res_list = self.index_relations_words.get('wr', rel_index)
        elif relation_type in ['friend', 'follower']:
            res_list = self.index_relations_users.get('ur', rel_index)
        else:
            return None

        if len(res_list):
            return res_list[0]

    def save_user_message(self, message, user_node):
        """
        :param message:
        :return:
        """
        previous_el = None
        for token in message:
            token_node = self.db.nodes.create(**token)
            token_node.labels.add('word')
            self.index_words.add('content', token.get('content'), token_node)
            #word - [comes] - word
            if previous_el:
                rel_data = self.get_relation_data(previous_el, token_node, rt_comes)
                count = rel_data.get('count') + 1 if rel_data else 1
                self.save_relation(previous_el, token_node, rt_comes, {'count': count})

            #user - [say] - word
            rel_data = self.get_relation_data(user_node, token_node, rt_say)
            count = rel_data.get('count') + 1 if rel_data else 1
            self.save_relation(token_node, user_node, rt_say, {'count': count})

            previous_el = token_node

    def get_users(self):
        return self.index_users.iteritems()

    def save_user(self, user):
        user_node = self.db.nodes.create(**user)
        user_node.labels.add('user')
        self.index_users.add('sn_id', user.get(u'id'), user_node)
        return user_node

    def save_social_object(self, s_object):
        raise NotImplementedError


    def get_paths(self, from_node, to_node, rel_type, direct=False):
        result = self.db.query(q="""
        START f_n=node(%s), t_n=node(%s)
        MATCH p = shortestPath(f_n-[:%s*]-%st_n)
        RETURN p, length(p)
         """ % (from_node.id, to_node.id, rel_type, '>' if direct else ''),
                               returns=([], text_type))
        print result
        return result


@stopwatch
def test_user_loads(ttr):
    neo = Neo4j_handler(truncated=True)

    def save_friends(user, depth=0):
        if depth > 3:
            return
        else:
            depth += 1
        n_user = neo.save_user(user)
        user1_friends_ids = ttr.get_related_users(user_id=user.get(u'id'), relation_type='friends')
        for el in user1_friends_ids[0:10 if len(user1_friends_ids) > 10 else len(user1_friends_ids)]:
            user_friend = ttr.get_user(user_id=el)
            n_user_friend = neo.save_user(user_friend)
            neo.save_relation(n_user, n_user_friend, relation_type='friend')
            save_friends(user_friend, depth)

    user = ttr.get_user(screen_name='linoleum2k12')
    save_friends(user)


if __name__ == '__main__':
    # Neo4j_handler(truncated=True)
    from contrib.api.ttr import __TTR_API

    ttr = __TTR_API()
    # test_user_loads(ttr)
    ttr.get_relations(screen_name='linoleum2k12')