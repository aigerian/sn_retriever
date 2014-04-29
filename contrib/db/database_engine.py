#coding: utf-8
from datetime import datetime
from urllib import addbase
from bson import DBRef, ObjectId
from contrib.api.entities import APIUser, APIMessage
from contrib.db import DataBase

from neo4jrestclient.client import GraphDatabase, IndexKey, Node, Relationship
from neo4jrestclient.exceptions import TransactionException
from neo4jrestclient.utils import text_type

__author__ = '4ikist'

import logging

import pymongo
from pymongo.errors import ConnectionFailure, DuplicateKeyError

from properties import *


log = logging.getLogger('database')


class GraphDataBaseMixin(object):
    def __init__(self, truncate):
        self.db = GraphDatabase(gdb_host)
        if truncate:
            tx = self.db.transaction(for_query=True)
            tx.append("MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r")
            tx.commit()

        with self.db.transaction() as tx:
            self.node_index = self.db.nodes.indexes.create('users')
            self.relationships_index = self.db.relationships.indexes.create('relations')
            tx.commit()

    def __create_relation_index_name(self, f, t, rtype):
        return '_'.join([str(f), str(t), str(rtype)])

    def get_node(self, user_id):
        node_index = self.node_index.get('id', user_id)
        if isinstance(node_index, IndexKey) or not len(node_index):
            return None
        return node_index[0]

    def save_user_node(self, user_id):
        node = self.get_node(user_id)
        if not node:
            node = self.db.nodes.create(id=user_id)
            self.node_index.add('id', user_id, node)
        return node

    def update_relations(self, new_rels, old_rels):
        from_id = old_rels[0].get('from')
        rel_type = old_rels[0].get('type')
        #delete old relations
        for i in xrange(len(old_rels) / 100 + 1):
            self.db.query(q="""
                START f=node(*), t=node(*)
                MATCH f-[rel:%s]->t
                WHERE f.id = %s AND t.id IN [%s]
                DELETE rel
                """ % (rel_type, from_id, ','.join([str(el.get('to')) for el in old_rels[i * 100:(i + 1) * 100]])))

        #save new relations
        for new_rel in new_rels:
            self.save_relation(from_id, new_rel.get('to'), rel_type)

    def save_relation(self, from_user_id, to_user_id, relation_type):
        if not isinstance(from_user_id, str) and not isinstance(to_user_id, str):
            from_user_id, to_user_id = str(from_user_id), str(to_user_id)
        f, t = self.save_user_node(from_user_id), self.save_user_node(to_user_id)
        rel = self.db.relationships.create(f, relation_type, t)
        self.relationships_index.add(relation_type,
                                     self.__create_relation_index_name(from_user_id, to_user_id, relation_type),
                                     rel)
        return rel

    def get_path(self, from_user_id, to_user_id, relation_type, only_nodes=False, only_length=True, directed=True):
        def accumulate_nodes(elements):
            result = [el.get('data').get(u'id') for el in elements]
            return result

        with self.db.transaction() as tx:
            from_node, to_node = self.get_node(from_user_id), self.get_node(to_user_id)
            tx.commit()

        if not from_node or not to_node or not isinstance(from_node, Node) or not isinstance(to_node, Node):
            return None

        if only_length:
            returns = 'length(p)'
            returns_param = text_type
        elif only_nodes:
            returns = 'NODES(p)[1..-1]'
            returns_param = accumulate_nodes
        else:
            returns = 'p'
            returns_param = 'path'

        query_result = self.db.query(q="""
        START f_n=node(%s), t_n=node(%s)
        MATCH p = shortestPath(f_n-[:%s*..1000]-%st_n)
        RETURN %s
         """ % (from_node.id,
                to_node.id,
                relation_type,
                '>' if directed else '',
                returns
        ), returns=returns_param)
        if len(query_result):
            return query_result[0][0]
        else:
            return None


class DataBasePathException(Exception):
    pass


class DataBaseMessageException(Exception):
    pass


class DataBaseRelationException(Exception):
    pass


class DataBaseUserException(Exception):
    pass


class Persistent(object):
    def __create_index(self, collection, field_or_list, direction, unique, **index_kwargs):
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

    def __init__(self, truncate=False):
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
        self.__create_index(self.messages, 'sn_id', pymongo.ASCENDING, True)
        self.__create_index(self.messages, 'user', pymongo.ASCENDING, False)
        self.__create_index(self.messages, 'text', 'text', False, language_override='lang')

        self.users = self.database['users']
        self.__create_index(self.users, 'sn_id', pymongo.ASCENDING, True)
        self.__create_index(self.users, 'screen_name', pymongo.ASCENDING, True)

        self.social_objects = self.database['social_objects']
        self.__create_index(self.social_objects, 'sn_id', pymongo.ASCENDING, True)

        self.relations = self.database['relations']
        self.__create_index(self.relations, ['from', 'to', 'type'], pymongo.ASCENDING, True)
        self.__create_index(self.relations, 'update_date', pymongo.ASCENDING, False)
        self.__create_index(self.relations, 'position', pymongo.ASCENDING, False)

        self.not_loaded_users = self.database['not_loaded_users']

        self.graph_db = GraphDataBaseMixin(truncate)

        if truncate:
            self.users.remove()
            self.messages.remove()
            self.relations.remove()
            self.social_objects.remove()
            self.not_loaded_users.remove()

    def get_created_at(self, object_type, object_sn_id):
        object_type += 's'
        if object_type in self.database.collection_names(include_system_collections=False):
            return self.database[object_type].find_one({'sn_id': object_sn_id})
        return None

    def get_user_ref(self, user):
        return DBRef(self.users.name, user.get('_id'))

    def get_users(self, parameter=None):
        users = self.users.find(parameter)
        return [APIUser(el, from_db=True) for el in users]

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
            request_params['screen_name'] = screen_name[1:] if '@' == screen_name[0] else screen_name
        else:
            return None
        user = self.users.find_one(request_params)
        if use_as_cache and user and (datetime.now() - user.get('update_date')).seconds > user_cache_time:
            return None
        if user:
            return APIUser(user, from_db=True)

    def save_user(self, user, update=True):
        if user.get('screen_name') is None:
            raise DataBaseUserException('user have not screen_name')
        if update:
            result = self._save_or_update_object(self.users, user['sn_id'], user)
        else:
            result = self.users.save(user)
        self.not_loaded_users.remove({'user_ref': DBRef(self.users.name, result)})
        self.graph_db.save_user_node(str(result))
        return result

    def get_messages_by_text(self, text, limit=100, score_more_than=1):
        result = self.database.command('text', self.messages.name, search=text, limit=limit)
        messages = map(lambda x: x['obj'], filter(lambda x: x['score'] >= score_more_than, result['results']))
        return messages

    def get_messages(self, parameter):
        result = self.messages.find(parameter).sort('created_at', -1)
        result = [APIMessage(el, from_db=True) for el in result]
        return result

    def get_message_last(self, user):
        result = list(self.messages.find({'user.$id': user.get('_id')}).sort('created_at', -1).limit(1))
        if len(result):
            return APIMessage(result[0], from_db=True)

    def get_message(self, sn_id, use_as_cache=False):
        message = self.messages.find_one({'sn_id': sn_id})
        if use_as_cache and message and (datetime.now() - message.get('update_date')).seconds > message_cache_time:
            return None
        if message:
            return APIMessage(message, from_db=True)

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
                    raise DataBaseMessageException('No user for this sn_id [%s]' % user_sn_id)

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

    def save_relations_for_diff(self, from_id, new_relation_set, relation_type, added_rels, removed_rels):
        def find_or_create_user(sn_id):
            user = self.get_user(sn_id=sn_id)
            if not user:
                user_id = self.users.save({'sn_id': sn_id})
                self.not_loaded_users.save({'user_ref': DBRef(self.users.name, user_id)})
                return user_id
            return user.get('_id')

        for position, relation in enumerate(new_relation_set.reverse()):
            to = find_or_create_user(sn_id=relation)
            self.save_relation(from_=from_id, to_=to, relation_data={'type': relation_type}, position=position)

        self.graph_db.update_relations(added_rels, removed_rels)

    def get_related_users(self, from_id=None, to_id=None, relation_type=None, result_key=None):
        """
        :param from_id - if it is none - return users which from to to_id (subject - [relation_type] -> user with to_id)
        else: (user with from_id - [relation_type] -> subject)
        :param result_key - key of user if None - user object
        :returns related users which related from or to or some user's element (retrieve by param: result_key)
        """
        params = {}
        if from_id:
            params['from'] = from_id
        if to_id:
            params['to'] = to_id
        if relation_type:
            params['type'] = relation_type
        out_refs = self.relations.find(params).sort('position')
        result = []
        for el in out_refs:
            result_element = self.get_user(_id=el.get('to') if params.has_key('from') else el.get('from'))
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
        rel_type = relation_data.pop('type')
        log.info('saving relation [%s] - [%s] -> [%s] with relation data:\n %s' % (from_, rel_type, to_, relation_data))
        try:
            result = self.relations.save({'from': from_, 'to': to_,
                                          'type': rel_type,
                                          'data': relation_data,
                                          'update_date': datetime.now(),
                                          'position': position
            })
            self.graph_db.save_relation(from_, to_, rel_type)
            return result
        except Exception as e:
            log.exception(e)
            log.warn('can not save relation: %s -[%s]-> %s [%s] \n%s' % (from_, to_, rel_type, position, e))


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


class GraphPersistent(Persistent):
    def __init__(self, *args, **kwargs):
        super(GraphPersistent, self).__init__(*args, **kwargs)

    def __get_user_graph_id(self, stuff):
        if isinstance(stuff, str):
            return stuff
        if isinstance(stuff, APIUser):
            return str(stuff.get('_id'))
        if isinstance(stuff, ObjectId):
            return str(stuff)

    def get_path_length(self, from_user, to_user, relation_type, directed=True):
        result = self.graph_db.get_path(self.__get_user_graph_id(from_user), self.__get_user_graph_id(to_user),
                                        relation_type, directed=directed)
        if result:
            return int(result)
        else:
            return None

    def get_path_users(self, from_user, to_user, relation_type, directed=True):
        gdb_result = self.graph_db.get_path(self.__get_user_graph_id(from_user), self.__get_user_graph_id(to_user),
                                            relation_type, only_nodes=True, only_length=False, directed=directed)
        if gdb_result is None:
            return None
        result = [self.get_user(_id=el) for el in gdb_result]
        return result


if __name__ == '__main__':
    pass