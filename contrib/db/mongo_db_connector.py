#coding: utf-8
from datetime import datetime
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
        except pymongo.errors.ConfigurationError as e:
            self.engine = pymongo.MongoClient(db_host, db_port)
        except ConnectionFailure as e:
            log.error('can not connect to database server %s' % e)
            exit(-1)
        except Exception as e:
            log.exception(e)

        self.database = self.engine[db_name]

        self.messages = self.database['messages']
        if len(self.messages.index_information()) <= 1:
            self.messages.ensure_index([('sn_id', pymongo.ASCENDING), ], unique=True)

        self.users = self.database['users']
        if len(self.users.index_information()) <= 1:
            self.users.ensure_index([('sn_id', pymongo.ASCENDING)], unique=True)

        self.social_objects = self.database['social_objects']
        if len(self.social_objects.index_information()) <= 1:
            self.social_objects.ensure_index([('sn_id', pymongo.ASCENDING)], unique=True)

        self.relations = self.database['relations']
        if len(self.relations.index_information()) <= 1:
            self.relations.ensure_index(
                [('from', pymongo.ASCENDING), ('to', pymongo.ASCENDING), ('type', pymongo.ASCENDING)], unique=True)

        self.duty = self.database['duty']

    def get_users(self):
        users = self.users.find()
        return [el for el in users]

    def get_user(self, _id=None, sn_id=None):
        request_params = {}
        if _id:
            request_params['_id'] = _id
        elif sn_id:
            request_params['sn_id'] = sn_id
        else:
            return None
        user = self.users.find_one(request_params)
        return user

    def save_message(self, message):
        log.info('saving message: \n%s' % message)
        result = self._save_or_update_object(self.messages, message['sn_id'], message)
        log.info('id object result: \n%s' % result)
        return result

    def save_user(self, user):
        user['update_date'] = datetime.now()
        result = self._save_or_update_object(self.users, user['sn_id'], user)
        return result


    def save_social_object(self, s_object):
        log.info('saving social object \n%s' % s_object)
        result = self._save_or_update_object(self.social_objects, s_object['sn_id'], s_object)
        log.info('id object result: \n%s' % result)
        return result

    def save_relation(self, from_, to_, relation_data=None):
        log.info('saving relation [%s] ---> [%s] with relation data:\n %s' % (from_, to_, relation_data))
        result = self.relations.save({'from': from_, 'to': to_, 'data': relation_data,
                                      'type': relation_data.get('type') if relation_data else None})
        return result


    def _save_or_update_object(self, sn_object, sn_id, object_data):
        """
        saving or updating object with social_name social_id and user_data
        always return _id of user in database
        """
        assert sn_id

        log.info('saving object: [%s]\n%s' % (sn_id, object_data))
        founded_user = sn_object.find_one({'sn_id': sn_id})
        if founded_user:
            founded_user = dict(founded_user)
            founded_user.update(object_data)
            sn_object.save(founded_user)
            result = founded_user.get('_id')
        else:
            result = sn_object.save(object_data)

        return result

    def save_duty(self, duty_object, update_by_what=None):
        log.info('saving duty: %s %s' % (duty_object, ('(updating): %s' % (update_by_what)) if update_by_what else ''))
        if update_by_what:
            result = self.duty.find_one({'work': update_by_what})
            if result:
                result.update(duty_object)
                self.duty.save(result)

        self.duty.save(duty_object)

    def get_duty(self, duty_q):
        log.info('getting duty by: %s' % duty_q)
        return self.duty.find_one(duty_q)


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






