#coding: utf-8
from contrib.db import DataBase

__author__ = '4ikist'

import logging

import pymongo
from pymongo.errors import ConnectionFailure

from properties import *


log = logging.getLogger('database')


class db_handler(DataBase):
    def __init__(self):
        mongo_uri = 'mongodb://%s:%s@%s:%s/%s' % (db_user, db_password, db_host, db_port, db_name)
        try:
            self.engine = pymongo.MongoClient(mongo_uri)
        except ConnectionFailure as e:
            log.error('can not connect to database server')
            exit(-1)

        self.database = self.engine[db_name]

        self.messages = self.database['messages']
        if len(self.messages.index_information()) <= 1:
            self.messages.ensure_index([('sn_id', pymongo.ASCENDING), ('sn_name', pymongo.ASCENDING)], unique=True)

        self.users = self.database['users']
        if len(self.users.index_information()) <= 1:
            self.users.ensure_index([('sn_id', pymongo.ASCENDING), ('sn_name', pymongo.ASCENDING)], unique=True)

        self.social_objects = self.database['social_objects']
        if len(self.social_objects.index_information()) <= 1:
            self.social_objects.ensure_index([('sn_id', pymongo.ASCENDING), ('sn_name', pymongo.ASCENDING)],
                                             unique=True)

        self.relations = self.database['relations']
        if len(self.relations.index_information()) <= 1:
            self.relations.ensure_index(
                [('from', pymongo.ASCENDING), ('to', pymongo.ASCENDING), ('type', pymongo.ASCENDING)], unique=True)


    def get_users(self):
        users = self.users.find()
        return [el for el in users]

    def get_user(self, user_id):
        user = self.users.find_one({'_id': user_id})
        return user

    def save_message(self, message):
        log.info('saving message: \n%s' % message)
        result = self._save_or_update_object(self.messages, message['sn_id'], message['sn_name'], message)
        log.info('id object result: \n%s' % result)
        return result

    def save_user(self, user):
        log.info('saving user: \n%s' % user)
        result = self._save_or_update_object(self.users, user['sn_id'], user['sn_name'], user)
        log.info('id object result: \n%s' % result)
        return result

    def save_social_object(self, s_object):
        log.info('saving social object \n%s' % s_object)
        result = self._save_or_update_object(self.social_objects, s_object['sn_id'], s_object['sn_name'], s_object)
        log.info('id object result: \n%s' % result)
        return result

    def save_relation(self, from_, to_, relation_data=None):
        log.info('saving relation [%s] ---> [%s] with relation data:\n %s' % (from_, to_, relation_data))
        result = self.relations.save({'from': from_, 'to': to_, 'data': relation_data,
                                      'type': relation_data.get('type') if relation_data else None})
        return result


    def _save_or_update_object(self, sn_object, sn_id, sn_name, user_data):
        """
        saving or updating object with social_name social_id and user_data
        always return _id of user in database
        """
        assert sn_id
        assert sn_name
        log.info('saving object: [%s] in [%s]\n%s' % (sn_id, sn_name, user_data))
        founded_user = sn_object.find_one({'sn_id': sn_id, 'sn_name': sn_name})
        if founded_user:
            founded_user = dict(founded_user)
            founded_user.update(user_data)
            sn_object.save(founded_user)
            result = founded_user.get('_id')
        else:
            user = {'sn_id': sn_id, 'sn_name': sn_name}
            user.update(user_data)
            result = sn_object.save(user)

        return result


if __name__ == '__main__':
    db = db_handler()
    user_id1 = db.save_user({'sn_id': '1', 'sn_name': 'test', 'name': 'test', 'another_param': 'test'})
    user_id1_1 = db.save_user(
        {'sn_id': '1', 'sn_name': 'test', 'name': 'test_1', 'another_param': 'test_1', 'data_faka': 'tttratte!'})
    assert user_id1 == user_id1_1

    assert db.get_user(user_id1).get('data_faka') == 'tttratte!'

    user_id2 = db.save_user({'sn_id': '2', 'sn_name': 'test', 'name': 'test', 'another_param': 'test'})
    assert user_id1 != user_id2
    user_id3 = db.save_user({'sn_id': '3', 'sn_name': 'test', 'name': 'test', 'another_param': 'test'})
    assert user_id1 != user_id3






