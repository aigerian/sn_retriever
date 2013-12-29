# coding=utf-8

__author__ = '4ikist'

import logging

from py2neo import neo4j, node

from contrib.db import DataBase
import properties

#temp imports
from contrib.utils import process_message

rt_say = 'SAY'
rt_comes = 'COMES'

log = logging.getLogger('gdb')


class Neo4j_handler(DataBase):
    @staticmethod
    def create_relation_index(f, t, rtype):
        return '_'.join([str(f), str(t), str(rtype)])

    def __init__(self, truncated=False):
        self.db = neo4j.GraphDatabaseService(properties.gdb_host)
        if truncated:
            self.db.clear()

        self.index_users = self.db.get_or_create_index(neo4j.Node, 'users')
        self.index_words = self.db.get_or_create_index(neo4j.Node, 'words')

        self.index_relations_users = self.db.get_or_create_index(neo4j.Relationship, 'words_relations')
        self.index_relations_words = self.db.get_or_create_index(neo4j.Relationship, 'users_relations')
        self.index_relations_hybrid = self.db.get_or_create_index(neo4j.Relationship, 'hybrid_relations')

    def get_user(self, user_id):
        result_list = self.index_users.get('sn_id', user_id)
        if len(result_list):
            return result_list[0]
        return None

    def save_relation(self, from_, to_, relation_type='friend', relation_data={}):
        rel, = self.db.create((from_, relation_type, to_, relation_data))
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
            token_node, = self.db.create(node(token))
            token_node.add_labels('word')
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

    def get_users(self, prop_name=None, prop_val=None):
        return self.db.find('user', prop_name, prop_val)

    def save_user(self, user):
        log.info('saving user:\n%s' % user)
        user_node, = self.db.create(node(user))
        user_node.add_labels('user')
        self.index_users.add('sn_id', user.get(u'id'), user_node)
        return user_node

    def save_social_object(self, s_object):
        raise NotImplementedError


    def get_path(self, from_node, to_node):
        pass



if __name__ == '__main__':
    from contrib.api.ttr import TTR_API

    ttr = TTR_API()
    user = ttr.get_user(screen_name='linoleum2k12')

    user2_id = ttr.get_relations(user.get(u'id'))[0]
    user2 = ttr.get_user(user_id=user2_id)

    neo = Neo4j_handler(truncated=True)
    uid1 = neo.save_user(user)
    uid2 = neo.save_user(user2)

    neo.save_relation(uid1, uid2, 'friend')
    neo.save_relation(uid2, uid1, 'follower')

    timeline = ttr.get_user_timeline(screen_name='linoleum2k12')
    for el in timeline:
        text = el.get(u'text')
        message = process_message(text)
        neo.save_user_message(message, uid1)

    user1_saved = neo.get_user(user.get(u'id'))
    assert user1_saved == uid1
