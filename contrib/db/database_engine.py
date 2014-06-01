#coding: utf-8
from contrib.api.entities import APIUser, APIMessage

import redis

__author__ = '4ikist'

import pymongo
from pymongo.errors import ConnectionFailure, DuplicateKeyError

from properties import *


log = logging.getLogger('database')


# class GraphDataBaseMixin(object):
#     def __init__(self, truncate):
#         self.db = GraphDatabase(gdb_host)
#         if truncate:
#             tx = self.db.transaction(for_query=True)
#             tx.append("MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r")
#             tx.commit()
#
#         with self.db.transaction() as tx:
#             self.node_index = self.db.nodes.indexes.create('users')
#             self.relationships_index = self.db.relationships.indexes.create('relations')
#             tx.commit()
#
#     def __create_relation_index_name(self, f, t, rtype):
#         return '_'.join([str(f), str(t), str(rtype)])
#
#     def get_node(self, user_id):
#         node_index = self.node_index.get('id', user_id)
#         if isinstance(node_index, IndexKey) or not len(node_index):
#             return None
#         return node_index[0]
#
#     def save_user_node(self, user_id):
#         node = self.get_node(user_id)
#         if not node:
#             node = self.db.nodes.create(id=user_id)
#             self.node_index.add('id', user_id, node)
#         return node
#
#     def update_relations(self, new_rels, old_rels):
#         from_id = old_rels[0].get('from')
#         rel_type = old_rels[0].get('type')
#         #delete old relations
#         for i in xrange(len(old_rels) / 100 + 1):
#             self.db.query(q="""
#                 START f=node(*), t=node(*)
#                 MATCH f-[rel:%s]->t
#                 WHERE f.id = %s AND t.id IN [%s]
#                 DELETE rel
#                 """ % (rel_type, from_id, ','.join([str(el.get('to')) for el in old_rels[i * 100:(i + 1) * 100]])))
#
#         #save new relations
#         for new_rel in new_rels:
#             self.save_relation(from_id, new_rel.get('to'), rel_type)
#
#     def save_relation(self, from_user_id, to_user_id, relation_type):
#         if not isinstance(from_user_id, str) and not isinstance(to_user_id, str):
#             from_user_id, to_user_id = str(from_user_id), str(to_user_id)
#         f, t = self.save_user_node(from_user_id), self.save_user_node(to_user_id)
#         rel = self.db.relationships.create(f, relation_type, t)
#         self.relationships_index.add(relation_type,
#                                      self.__create_relation_index_name(from_user_id, to_user_id, relation_type),
#                                      rel)
#         return rel
#
#     def get_path(self, from_user_id, to_user_id, relation_type, only_nodes=False, only_length=True, directed=True):
#         log.info('getting path length [%s]-[%s]->[%s]' % (from_user_id, relation_type, to_user_id))
#
#         def accumulate_nodes(elements):
#             result = [el.get('data').get(u'id') for el in elements]
#             return result
#
#         with self.db.transaction() as tx:
#             from_node, to_node = self.get_node(from_user_id), self.get_node(to_user_id)
#             tx.commit()
#
#         if not from_node or not to_node or not isinstance(from_node, Node) or not isinstance(to_node, Node):
#             return None
#
#         if only_length:
#             returns = 'length(p)'
#             returns_param = text_type
#         elif only_nodes:
#             returns = 'NODES(p)[1..-1]'
#             returns_param = accumulate_nodes
#         else:
#             returns = 'p'
#             returns_param = 'path'
#
#         query_result = self.db.query(q="""
#         START f_n=node(%s), t_n=node(%s)
#         MATCH p = shortestPath(f_n-[:%s*..1000]-%st_n)
#         RETURN %s
#          """ % (from_node.id,
#                 to_node.id,
#                 relation_type,
#                 '>' if directed else '',
#                 returns
#         ), returns=returns_param)
#         if len(query_result):
#             return query_result[0][0]
#         else:
#             return None


class RedisBaseMixin(object):
    def __init__(self, truncate=False):
        self.engine = redis.StrictRedis(host=redis_host, port=redis_port, db=0)
        if truncate:
            self.engine.flushdb()


    def get_list_name(self, from_, type_):
        return '%s:%s' % (from_, type_)

    def save_relations(self, from_, to_, rel_type):
        list_name = self.get_list_name(from_, rel_type)
        if isinstance(to_, list):
            for i in xrange((len(to_) / redis_batch_size) + 1):
                log.debug("save: %s:%s " % (i * redis_batch_size, (i + 1) * redis_batch_size))
                self.engine.rpush(list_name,
                                  *to_[i * redis_batch_size:(i + 1) * redis_batch_size])
        else:
            self.engine.rpush(list_name, to_)
        return list_name


    def get_rels(self, from_, rel_type):
        return self.engine.lrange(self.get_list_name(from_, rel_type), 0, -1)

    def get_count(self, from_, rel_type):
        return self.engine.llen(self.get_list_name(from_, rel_type))

    def get_rels_and_remove(self, from_, rel_type):
        list_name = self.get_list_name(from_, rel_type)
        result = self.engine.lrange(list_name, 0, -1)
        self.engine.ltrim(list_name, 0, 0)
        self.engine.lpop(list_name)
        return result

    def remove_rel(self, from_, rel_type, to_):
        list_name = self.get_list_name(from_, rel_type)
        self.engine.lrem(list_name, 0, to_)
        return list_name


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
        self.__create_index(self.users, 'screen_name', pymongo.ASCENDING, False)

        self.social_objects = self.database['social_objects']
        self.__create_index(self.social_objects, 'sn_id', pymongo.ASCENDING, True)

        self.not_loaded_users = self.database['not_loaded_users']
        # self.__create_index(self.not_loaded_users, 'sn_id', pymongo.ASCENDING, True)

        self.relations_metadata = self.database['relations_metadata']
        self.__create_index(self.relations_metadata, 'relations_of', pymongo.ASCENDING, True)

        self.extended_user_info = self.database['extended_user_info']
        self.__create_index(self.extended_user_info, 'user_id', pymongo.ASCENDING, True)

        self.redis = RedisBaseMixin(truncate)

        if truncate:
            self.users.remove()
            self.messages.remove()
            self.social_objects.remove()
            self.not_loaded_users.remove()
            self.relations_metadata.remove()

    def get_user_ref(self, user):
        return DBRef(self.users.name, user.get('_id'))

    def get_users(self, parameter=None):
        if parameter and isinstance(parameter, dict) and parameter.get('screen_name'):
            parameter['screen_name'] = parameter.get('screen_name').lower()

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
            request_params['screen_name'] = screen_name[1:].lower() if '@' == screen_name[0] else screen_name.lower()
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
        result = [int(el) for el in self.redis.get_rels_and_remove(from_id, relation_type)]
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
        list_name = self.redis.remove_rel(from_id, relation_type, to_id)
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
        refs = self.redis.get_rels(from_id, relation_type)
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
        result = self.relations_metadata.find_one({'relations_of': self.redis.get_list_name(from_id, relation_type)})
        if result:
            return result.get('update_date')
        return None

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


if __name__ == '__main__':
    import random
    from datetime import datetime

    r = RedisBaseMixin(truncate=True)

    r.save_relations(1, [random.randint(0, 1000) for el in range(10)], 'friends')
    print r.get_count(1, 'friends')
    print r.get_rels(1, 'friends')
    print r.get_rels_and_remove(1, 'friends')
    print r.get_rels(1, 'friends')