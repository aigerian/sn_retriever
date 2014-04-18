#coding: utf-8
from datetime import datetime
from bson import DBRef
from contrib.db import DataBase

__author__ = '4ikist'

import logging

import pymongo
from pymongo.errors import ConnectionFailure

from properties import *


log = logging.getLogger('database')


class MongoHandlerMessageException(Exception):
    pass


class MongoHandlerRelationException(Exception):
    pass


class db_handler(DataBase):
    def create_index(self, collection, field_or_list, direction, unique, **index_kwargs):
        index_info = collection.index_information()
        if isinstance(field_or_list, list):
            index_name = ('_%s_' % direction).join(field_or_list)[:-1]
            index_param = [(el, direction) for el in field_or_list]
        else:
            index_name = '%s_%s' % (field_or_list, direction)
            index_param = [(field_or_list, direction)]

        if index_name in index_info:
            return
        else:
            collection.ensure_index(index_param, unique=unique, **index_kwargs)


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
        self.create_index(self.messages, 'sn_id', pymongo.ASCENDING, True)
        self.create_index(self.messages, 'user', pymongo.ASCENDING, False)
        self.create_index(self.messages, 'text', 'text', False, language_override='lang')

        self.users = self.database['users']
        self.create_index(self.users, 'sn_id', pymongo.ASCENDING, True)
        self.create_index(self.users, 'screen_name', pymongo.ASCENDING, True)

        self.social_objects = self.database['social_objects']
        self.create_index(self.social_objects, 'sn_id', pymongo.ASCENDING, True)

        self.relations = self.database['relations']
        self.create_index(self.relations, ['from', 'to', 'type'], pymongo.ASCENDING, True)
        self.create_index(self.relations, 'update_date', pymongo.ASCENDING, False)
        self.create_index(self.relations, 'position', pymongo.ASCENDING, False)

        self.duty = self.database['duty']
        self.not_loaded_users = self.database['not_loaded_users']

    def get_created_at(self, object_type, object_sn_id):
        object_type += 's'
        if object_type in self.database.collection_names(include_system_collections=False):
            return self.database[object_type].find_one({'sn_id': object_sn_id})
        return None

    def get_user_ref(self, user):
        return DBRef(self.users.name, user.get('_id'))

    def get_users(self, parameter=None):
        users = self.users.find(parameter)
        return [el for el in users]

    def get_user(self, _id=None, sn_id=None, screen_name=None, use_as_cache=False):
        """
        finding user by id in db or social net id or screen_name
        if use_as_cache - returning none if user update_date is out of date
        cache time in properties (in seconds)
        """
        request_params = {}
        if _id:
            request_params['_id'] = _id
        elif sn_id:
            request_params['sn_id'] = sn_id
        elif screen_name:
            request_params['screen_name'] = screen_name
        else:
            return None
        user = self.users.find_one(request_params)
        if use_as_cache and user and (datetime.now() - user.get('update_date')).seconds > user_cache_time:
            return None
        return user

    def save_user(self, user):
        result = self._save_or_update_object(self.users, user['sn_id'], user)
        self.not_loaded_users.remove({'user_ref': DBRef(self.users.name, result)})
        return result

    def get_messages_by_text(self, text, limit=100, score_more_than=1):
        result = self.database.command('text', self.messages.name, search=text, limit=limit)
        messages = map(lambda x: x['obj'], filter(lambda x: x['score'] >= score_more_than, result['results']))
        return messages

    def get_messages(self, parameter=None):
        result = self.messages.find(parameter).sort('time', -1)
        result = [el for el in result]
        return result

    def get_message_last(self, user):
        result = list(self.messages.find({'user.$id': user.get('_id')}).sort('created_at',-1).limit(1))
        if len(result):
            return result[0]

    def get_message(self, sn_id, use_as_cache=False):
        message = self.messages.find_one({'sn_id': sn_id})
        if use_as_cache and message and (datetime.now() - message.get('update_date')).seconds > message_cache_time:
            return None
        return message

    def save_message(self, message):
        """
        saving message. message must be a dict with field user, this field must be a DbRef or dict ith sn_id of some user in db
        """
        if not isinstance(message.get('user'), DBRef):
            user_sn_id = message.get('user').get('sn_id')
            if user_sn_id:
                user = self.get_user(sn_id=user_sn_id)
                if user:
                    user_ref = self.get_user_ref(user)
                    message['user'] = user_ref
                else:
                    raise MongoHandlerMessageException('No user for this sn_id [%s]' % user_sn_id)

        result = self._save_or_update_object(self.messages, message['sn_id'], message)
        return result

    def save_social_object(self, s_object):
        result = self._save_or_update_object(self.social_objects, s_object['sn_id'], s_object)
        return result

    def retrieve_relations_for_diff(self, from_id, relation_type):
        found = self.relations.find({'from': from_id, 'type': relation_type}).sort('position')
        result = []
        for el in found:
            user = self.users.find_one({'_id': el.get('to')})
            result.append(user.get('sn_id'))
        self.relations.remove({'from': from_id, 'type': relation_type})
        return result

    def save_relations_for_diff(self, from_id, relations, relation_type):
        def find_or_create_user(sn_id):
            user = self.get_user(sn_id=sn_id)
            if not user:
                user_id = self.users.save({'sn_id': sn_id})
                self.not_loaded_users.save({'user_ref': DBRef(self.users.name, user_id)})
                return user_id
            return user.get('_id')

        for position, relation in enumerate(relations.reverse()):
            to = find_or_create_user(sn_id=relation)
            self.save_relation(from_=from_id, to_=to, relation_data={'type': relation_type}, position=position)

    def get_relations(self, from_id=None, to_id=None, relation_type=None, result_key=None):
        """
        :param result_key - key of user if None - user
        """
        out_refs = self.relations.find({'from': from_id, 'to': to_id, 'type': relation_type}).sort('position')
        result = []
        for el in out_refs:
            result_element = self.users.find_one({'_id': el.get('to')})
            if result_key is None:
                result.append(result_element)
            else:
                result.append(result_element.get(result_key))
        return result

    def save_relation(self, from_, to_, relation_data=None, position=None):
        """
        saving relation from and to must be id from database
        """
        if not relation_data: relation_data = {'type': None}
        if not position:
            rel_with_last_position = list(self.relations.find({'from': from_}).sort('position', -1).limit(1))
            if not len(rel_with_last_position):
                position = 1
            else:
                position = int(rel_with_last_position[0].get('position')) + 1
        log.info('saving relation [%s] ---> [%s] with relation data:\n %s' % (from_, to_, relation_data))
        result = self.relations.save({'from': from_, 'to': to_, 'data': relation_data,
                                      'type': relation_data.get('type'),
                                      'update_date': datetime.now(),
                                      'position': position
        })
        return result


    def _save_or_update_object(self, sn_object, sn_id, object_data):
        """
        saving or updating object with social_name social_id and user_data
        always return _id of user in database
        """
        assert sn_id is not None
        object_data['update_date'] = datetime.now()
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
    user_id = db.save_user({'sn_id': 123, 'another_data': 'test'})
    db.save_message({'sn_id': 123, 'user': {'sn_id': 123}, 'text': 'some text'})
    user_messages = db.get_messages({'user': db.get_user_ref({'_id': user_id})})
    print user_messages


