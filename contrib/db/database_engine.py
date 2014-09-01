# coding: utf-8

from datetime import datetime
import json
from bson import DBRef
from contrib.api.entities import APIUser, APIMessage, APIContentObject, APISocialObject
from pymongo import MongoClient, ASCENDING

import networkx as nx
from pymongo.errors import ConnectionFailure, ConfigurationError
import redis

from properties import *

__author__ = '4ikist'

log = logging.getLogger('database')


class DataBasePathException(Exception):
    pass


class DataBaseMessageException(Exception):
    pass


class DataBaseRelationException(Exception):
    pass


class DataBaseUserException(Exception):
    pass


class RGP_Node_Exception(Exception):
    pass


from_name = lambda x: '%s>' % x
to_name = lambda x: '%s<' % x
ref_name = lambda f, t, tp: '%s>%s(%s)' % (f, t, tp)
gfn = lambda x: x[0:x.index('>')]
gtn = lambda x: x[x.index('>') + 1: x.index('(')]


class RedisGraphPersistent(nx.DiGraph):
    def __init__(self, graph_name, truncate=False, **attr):
        super(RedisGraphPersistent, self).__init__(**attr)
        self.graph_name = graph_name
        self.engine = redis.StrictRedis(host=redis_host, port=redis_host, db=1)
        if truncate:
            self.engine.flushdb()

    def nodes_iter(self, data=False):
        nodes = self.engine.smembers('%s_nodes' % self.graph_name)
        for el in nodes:
            if not data:
                yield el
            else:
                yield self._get_data(el)

    def degree(self, nbunch=None, weight=None):
        return super(RedisGraphPersistent, self).degree(nbunch, weight)

    def degree_iter(self, nbunch=None, weight=None):
        pass

    def subgraph(self, nbunch):
        return super(RedisGraphPersistent, self).subgraph(nbunch)

    def has_edge(self, u, v):
        return super(RedisGraphPersistent, self).has_edge(u, v)

    def number_of_nodes(self):
        return super(RedisGraphPersistent, self).number_of_nodes()

    def remove_edge(self, u, v):
        return super(RedisGraphPersistent, self).remove_edge(u, v)

    def remove_edges_from(self, ebunch):
        super(RedisGraphPersistent, self).remove_edges_from(ebunch)

    def out_degree(self, nbunch=None, weight=None):
        return super(RedisGraphPersistent, self).out_degree(nbunch, weight)

    def in_edges(self, nbunch=None, data=False):
        return super(RedisGraphPersistent, self).in_edges(nbunch, data)

    def add_edge(self, u, v, attr_dict=None, **attr):
        return super(RedisGraphPersistent, self).add_edge(u, v, attr_dict, **attr)

    def neighbors_iter(self, n):
        return super(RedisGraphPersistent, self).neighbors_iter(n)

    def remove_node(self, n):
        return super(RedisGraphPersistent, self).remove_node(n)

    def is_directed(self):
        return super(RedisGraphPersistent, self).is_directed()

    def clear(self):
        super(RedisGraphPersistent, self).clear()

    def is_multigraph(self):
        return super(RedisGraphPersistent, self).is_multigraph()

    def has_successor(self, u, v):
        return super(RedisGraphPersistent, self).has_successor(u, v)

    def get_edge_data(self, u, v, default=None):
        return super(RedisGraphPersistent, self).get_edge_data(u, v, default)

    def add_path(self, nodes, **attr):
        super(RedisGraphPersistent, self).add_path(nodes, **attr)

    def has_node(self, n):
        return super(RedisGraphPersistent, self).has_node(n)

    def has_predecessor(self, u, v):
        return super(RedisGraphPersistent, self).has_predecessor(u, v)

    def size(self, weight=None):
        return super(RedisGraphPersistent, self).size(weight)

    def number_of_edges(self, u=None, v=None):
        return super(RedisGraphPersistent, self).number_of_edges(u, v)

    def in_degree_iter(self, nbunch=None, weight=None):
        return super(RedisGraphPersistent, self).in_degree_iter(nbunch, weight)

    def neighbors(self, n):
        return super(RedisGraphPersistent, self).neighbors(n)

    def adjacency_list(self):
        return super(RedisGraphPersistent, self).adjacency_list()

    def to_directed(self):
        return super(RedisGraphPersistent, self).to_directed()

    def remove_nodes_from(self, nbunch):
        super(RedisGraphPersistent, self).remove_nodes_from(nbunch)

    def add_nodes_from(self, nodes, **attr):
        super(RedisGraphPersistent, self).add_nodes_from(nodes, **attr)

    def out_degree_iter(self, nbunch=None, weight=None):
        return super(RedisGraphPersistent, self).out_degree_iter(nbunch, weight)

    def in_edges_iter(self, nbunch=None, data=False):
        if isinstance(nbunch, str):
            return self.predecessors_iter(nbunch)

    def add_node(self, n, attr_dict=None, **attr):
        self._save_data(n, attr_dict if attr_dict else {})
        return super(RedisGraphPersistent, self).add_node(n, attr_dict, **attr)


    def _save_data(self, name, dict):
        for k, v in dict.iteritems():
            self.engine.hset(name, k, json.dumps(v))

    def _get_data(self, name):
        result = self.engine.hgetall(name)
        return_obj = {}

        for i in xrange(len(result)):
            # field name
            if i % 2:
                return_obj[result[i]] = result[i + 1]

        return return_obj


    def save_node(self, node_data):
        if node_data.get('name', None) is None:
            raise RGP_Node_Exception('must be name in your node data:\n%s' % node_data)
        name = node_data.get('name')
        # for graph
        self.engine.sadd('%s_nodes' % self.graph_name, name)
        self._save_data(name, node_data)

    def save_ref(self, from_node_name, to_node_name, ref_type, ref_data=None):
        f, t, r_n = from_name(from_node_name), to_name(to_node_name), ref_name(from_node_name, to_node_name, ref_type)
        self._save_data(r_n, ref_data if ref_data else {})
        self.engine.sadd(f, r_n)
        self.engine.sadd(t, r_n)

    def predecessors_iter(self, n):
        for el in [gtn(el) for el in self.engine.smembers(from_name(n))]:
            yield el

    def successors_iter(self, n):
        for el in [gfn(el) for el in self.engine.smembers(to_name(n))]:
            yield el

    def get_shortest_path(self, from_node, to_node):
        print 'evaluating shortest path between %s -> %s' % (from_node, to_node)
        result = nx.shortest_path(self, from_node, to_node)
        return result


class RedisBaseMixin(object):
    def __init__(self, truncate=False):
        self.engine = redis.StrictRedis(host=redis_host, port=redis_port, db=0)
        if truncate:
            self.engine.flushdb()


    def form_relations_list_name(self, from_, type_):
        return '%s:%s' % (from_, type_)

    def form_path_list_name(self, from_, to_):
        return self.form_relations_list_name(from_, to_)

    def save_relations(self, from_, to_, rel_type):
        list_name = self.form_relations_list_name(from_, rel_type)
        if isinstance(to_, list):
            for i in xrange((len(to_) / redis_batch_size) + 1):
                log.debug("save: %s:%s " % (i * redis_batch_size, (i + 1) * redis_batch_size))
                self.engine.rpush(list_name,
                                  *to_[i * redis_batch_size:(i + 1) * redis_batch_size])
        else:
            self.engine.rpush(list_name, to_)
        return list_name


    def get_relations(self, from_, rel_type):
        return self.engine.lrange(self.form_relations_list_name(from_, rel_type), 0, -1)

    def get_count(self, from_, rel_type):
        return self.engine.llen(self.form_relations_list_name(from_, rel_type))

    def get_relations_and_remove(self, from_, rel_type):
        list_name = self.form_relations_list_name(from_, rel_type)
        result = self.engine.lrange(list_name, 0, -1)
        self.engine.ltrim(list_name, 0, 0)
        self.engine.lpop(list_name)
        return result

    def remove_relation(self, from_, rel_type, to_):
        list_name = self.form_relations_list_name(from_, rel_type)
        self.engine.lrem(list_name, 0, to_)
        return list_name

    def save_path(self, elements):
        p_name = self.form_path_list_name(elements[0], elements[-1])
        print p_name
        self.engine.rpush(p_name, *elements)
        return p_name

    def get_path(self, from_, to_):
        list_name = self.form_path_list_name(from_, to_)
        result = self.engine.lrange(list_name, 0, -1)
        return result

    def remove_path(self, from_, to_):
        list_name = self.form_path_list_name(from_, to_)
        self.engine.ltrim(list_name, 0, 0)
        self.engine.lpop(list_name)


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
            self.engine = MongoClient(mongo_uri)
        except ConfigurationError as e:
            self.engine = MongoClient(db_host, db_port)
        except ConnectionFailure as e:
            log.error('can not connect to database server %s' % e)
            exit(-1)
        except Exception as e:
            log.exception(e)

        self.database = self.engine[db_name]

        self.messages = self.database['messages']
        self.__create_index(self.messages, 'sn_id', ASCENDING, True)
        self.__create_index(self.messages, 'user', ASCENDING, False)
        self.__create_index(self.messages, 'text', 'text', False, language_override='lang')

        self.users = self.database['users']
        self.__create_index(self.users, 'sn_id', ASCENDING, True)
        self.__create_index(self.users, 'screen_name', ASCENDING, False)

        self.social_objects = self.database['social_objects']
        self.__create_index(self.social_objects, 'sn_id', ASCENDING, True)

        self.content_objects = self.database['content_objects']
        self.__create_index(self.social_objects, 'sn_id', ASCENDING, True)

        self.not_loaded_users = self.database['not_loaded_users']

        self.relations_metadata = self.database['relations_metadata']
        self.__create_index(self.relations_metadata, 'relations_of', ASCENDING, True)

        self.extended_user_info = self.database['extended_user_info']
        self.__create_index(self.extended_user_info, 'user_id', ASCENDING, True)

        self.changes = self.database['user_changes']
        self.__create_index(self.changes, 'sn_id', ASCENDING, False)
        self.__create_index(self.changes, 'datetime', ASCENDING, False)

        self.deleted_users = self.database['deleted_users']
        self.__create_index(self.deleted_users, 'sn_id', ASCENDING, True)

        self.redis = RedisBaseMixin(truncate)

        if truncate:
            self.users.remove()
            self.messages.remove()
            self.social_objects.remove()
            self.not_loaded_users.remove()
            self.relations_metadata.remove()
            self.changes.remove()
            self.deleted_users.remove()

    def add_deleted_user(self, user_sn_id):
        found = self.deleted_users.find_one({'sn_id': user_sn_id})
        if not found:
            self.deleted_users.save({'sn_id': user_sn_id})

    def save_user_changes(self, changes):
        assert changes.get('sn_id')
        assert changes.get('datetime')
        self.changes.save(changes)

    def update_user_date(self, user_sn_id):
        self.users.update({'sn_id': user_sn_id}, {'$set': {'update_date': datetime.now()}})

    def get_user_ref(self, user):
        return DBRef(self.users.name, user.get('_id'))

    def get_users(self, parameter=None):
        return [list(self.get_users_iter(parameter))]

    def get_users_iter(self, parameter=None):
        if parameter and isinstance(parameter, dict) and parameter.get('screen_name'):
            parameter['screen_name'] = parameter.get('screen_name').lower()
        users = self.users.find(parameter)
        for el in users:
            yield APIUser(el, from_db=True)

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
            request_params['screen_name'] = screen_name[1:].lower() if '@' == screen_name[
                0] else screen_name.lower()
        else:
            return None
        user = self.users.find_one(request_params)
        if use_as_cache and user and (datetime.now() - user.get('update_date')).seconds > user_cache_time:
            return None
        if user:
            return APIUser(user, from_db=True)

    def is_not_loaded(self, user_sn_id):
        result = self.not_loaded_users.find_one({'_id': user_sn_id})
        if result:
            return True
        result = self.users.find_one({'sn_id': user_sn_id})
        if not result:
            return True
        return False

    def save_user(self, user):
        screen_name = user.get('screen_name')
        if screen_name is None:
            raise DataBaseUserException('user have not screen_name')
        user['screen_name'] = screen_name.lower()
        result = self._save_or_update_object(self.users, user['sn_id'], user)
        self.not_loaded_users.remove({'_id': user.get('sn_id')})
        user['_id'] = result
        return result

    def get_messages_by_text(self, text, limit=100, score_more_than=1):
        result = self.database.command('text', self.messages.name, search=text, limit=limit)
        messages = map(lambda x: x['obj'], filter(lambda x: x['score'] >= score_more_than, result['results']))
        return messages

    def get_messages(self, parameter):
        result = self.messages.find(parameter).sort('created_at', -1)
        result = [APIMessage(el) for el in result]
        return result

    def get_message_last(self, user):
        result = list(self.messages.find({'user.$id': user.get('_id')}).sort('created_at', -1).limit(1))
        if len(result):
            return APIMessage(result[0])

    def get_message(self, sn_id, use_as_cache=False):
        message = self.messages.find_one({'sn_id': sn_id})
        if use_as_cache and message and (datetime.now() - message.get('update_date')).seconds > message_cache_time:
            return None
        if message:
            return APIMessage(message)

    def save_message(self, message):
        """
        saving message. message must be a dict with field user, this field must be a DbRef or dict ith sn_id of some user in db
        """
        if not isinstance(message.get('user'), DBRef):
            user_sn_id = message.get('user').get('sn_id')
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

    def save_content_object(self, s_object):
        result = self._save_or_update_object(self.content_objects, s_object['sn_id'], s_object)
        return result


    def retrieve_relations_for_diff(self, from_id, relation_type):
        result = [int(el) for el in self.redis.get_relations_and_remove(from_id, relation_type)]
        return result

    def save_relations_for_diff(self, from_id, new_relation_set, relation_type):
        list_name = self.redis.save_relations(from_id, new_relation_set, relation_type)
        self.update_relations_metadata(list_name)
        for el in new_relation_set:
            if not self.users.find_one({'sn_id': el}):
                self.not_loaded_users.save({'_id': el})

    def save_relation(self, from_id, to_id, relation_type):
        list_name = self.redis.save_relations(from_id, to_id, relation_type)
        self.update_relations_metadata(list_name)

    def remove_relation(self, from_id, to_id, relation_type):
        list_name = self.redis.remove_relation(from_id, relation_type, to_id)
        self.update_relations_metadata(list_name)

    def update_relations_metadata(self, metadata_name):
        res = self.relations_metadata.find_one({'relations_of': metadata_name})
        if res:
            res['update_date'] = datetime.now()
            self.relations_metadata.save(res)
        else:
            self.relations_metadata.save({'relations_of': metadata_name, 'update_date': datetime.now()})

    def get_related_users(self, from_id, relation_type, result_key=None, only_sn_ids=False):
        """
        :param from_id - if it is none - return users which from to to_id (subject - [relation_type] -> user with to_id)
        else: (user with from_id - [relation_type] -> subject)
        :param result_key - key of user if None - user object
        :returns related users which related from or to or some user's element (retrieve by param: result_key)
        """
        refs = self.redis.get_relations(from_id, relation_type)
        result = []
        for el in refs:
            if only_sn_ids:
                result.append(int(el))
                continue
            result_element = self.get_user(sn_id=int(el))
            if result_key is None:
                result.append(result_element)
            else:
                result.append(result_element.get(result_key))
        return result

    def get_relations_count(self, from_id, relations_type):
        return self.redis.get_count(from_id, relations_type)

    def get_relations_update_time(self, from_id, relation_type):
        result = self.relations_metadata.find_one(
            {'relations_of': self.redis.form_relations_list_name(from_id, relation_type)})
        if result:
            return result.get('update_date')
        return None

    def save_object_batch(self, object_batch):
        """
        сохраняет список объектов
        """
        for object in object_batch:
            if isinstance(object, APIMessage):
                self.save_message(object)
            elif isinstance(object, APIContentObject):
                self.save_content_object(object)
            elif isinstance(object, APISocialObject):
                self.save_social_object(object)
            else:
                log.warn('object have not supported entity\n%s' % object)

    def _save_or_update_object(self, sn_object, sn_id, object_data):
        """
        saving or updating object with social_name social_id and user_data
        always return _id of user in database
        """
        assert sn_id is not None
        object_data['update_date'] = datetime.now()
        log.debug('saving object: [%s]\n%s' % (object_data.get('screen_name') or sn_id, object_data))
        founded_user = sn_object.find_one({'sn_id': sn_id})
        if founded_user:
            founded_user = dict(founded_user)
            founded_user.update(object_data)
            sn_object.save(founded_user)
            result = founded_user.get('_id')
        else:
            result = sn_object.save(object_data)
        return result

    def save_extended_user_info(self, user_id, extended_info):
        saved = self.extended_user_info.find_one({'user_id': user_id})
        if saved:
            to_save = saved
            to_save['update_date'] = datetime.now()
            to_save.update(extended_info)
        else:
            to_save = extended_info
            to_save['update_date'] = datetime.now()
            to_save['user_id'] = user_id
        self.extended_user_info.save(to_save)

    def get_extended_user_info(self, user_id=None, **kwargs):
        params = {}
        if user_id:
            params['user_id'] = user_id
        params.update(kwargs)
        return self.extended_user_info.find_one(params)

    def save_path(self, elements):
        if isinstance(elements, list) and len(elements) > 1:
            self.redis.save_path(elements)

    def get_path(self, from_, to_):
        return self.redis.get_path(from_, to_)

    def remove_path(self, from_, to_):
        self.redis.remove_path(from_, to_)


if __name__ == '__main__':
    db = Persistent()
    db.save_path([1, 3, 4, 5, 6, 7, 8])
    db.save_path([1, 3, 4, 5, 6])
    db.get_path(1, 6)

