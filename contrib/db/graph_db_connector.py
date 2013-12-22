# coding=utf-8
__author__ = '4ikist'

from py2neo import neo4j, node
from contrib.db import DataBase
import properties


class Neo4j_handler(DataBase):
    def __init__(self):
        self.db = neo4j.GraphDatabaseService(properties.gdb_host)

    def get_user(self, user_id):
        pass

    def save_relation(self, from_, to_, relation_data=None):
        super(Neo4j_handler, self).save_relation(from_, to_, relation_data)

    def save_message(self, message):
        """
        :param message:
        :return:
        """

    def _process_message(self, message, entities=None):
        """
        :param message:
        :param entities:
        :return: list of hashes with type of words and inclusions
        """
        import re
        reg_word = re.compile(u'(@|#)?[a-zA-Zа-яА-Я0-9]+')


    def get_users(self):
        super(Neo4j_handler, self).get_users()

    def save_user(self, user):
        pre_saved = node(user)
        result = self.db.create(pre_saved)
        return result._id

    def save_social_object(self, s_object):
        super(Neo4j_handler, self).save_social_object(s_object)


