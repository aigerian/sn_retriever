#coding: utf-8
import time
import datetime

__author__ = '4ikist'

import logging

import pymongo
from pymongo.errors import ConnectionFailure

from properties import *


log = logging.getLogger('database')


class queue_handler(object):
    def __init__(self):
        mongo_uri = 'mongodb://%s:%s@%s:%s/%s' % (db_q_user, db_q_password, db_q_host, db_q_port, db_q_name)
        self.log = logging.getLogger('queue db handler')
        self.log.info('connecting: %s' % mongo_uri)
        try:
            self.engine = pymongo.MongoClient(mongo_uri)
        except ConnectionFailure as e:
            self.log.error('can not connect to database server')
            exit(-1)
        self.database = self.engine[db_q_name]

        self.targets = self.database['targets']
        self.statuses = self.database['statuses']
        self.result_store = self.database['cache']

    def get_new_target(self, who):
        self.log.info('getting new target for %s' % who)
        target = None
        while True:
            target = self.targets.find_and_modify({'status': NEW_STATUS}, {
                '$set': {'status': GETTED_STATUS, 'who': who, 'time_updated': int(time.time())}})
            if target:
                break
            time.sleep(GET_TARGET_PERIOD_SEC)
        return target


    def create_new_target(self, target, root):
        self.log.info('creating new target %s with root %s' % (target, root))
        self.targets.save({'body': target, 'status': 'new', 'root': root})

    def resolve_target(self, target_id, result_id):
        self.log.info('resolving target with id: %s, and result id:%s' % (target_id, result_id))
        target = self.targets.find_one({'_id': target_id})
        target.update({'status': ENDED_STATUS, 'result_id': result_id})
        self.targets.save(target)

    def update_bad_targets(self, whos):
        self.log.info('updating bad targets for workers: %s' % whos)
        result = self.targets.update({'status': GETTED_STATUS, 'who': {'$in': whos}},
                                     {'$set': {'status': NEW_STATUS}, '$unset': {'who': 1}})
        self.log.info(result)

    def set_worker_status(self, who, status_name=WORKED_STATUS):
        status = self.statuses.find_one({'who': who})
        if not status:
            self.statuses.insert({'updated': int(time.time()), 'who': who, 'status': status_name})
        else:
            self.statuses.update(status, {'$set': {'updated': int(time.time())}})

    def get_bad_workers(self):
        result = self.statuses.find({'updated': {'$lte': int(time.time()) - STATUS_REFRESH_PERIOD_SEC * 3}})
        return [el['who'] for el in result]

    def remove_db_workers(self, whos):
        self.log.info('removing bad workers %s' % whos)
        result = self.statuses.remove({'who': {'$in': whos}})
        self.log.info(result)

    def add_result(self, object, sn_name):
        self.log.info('adding result for %s in sn: %s' % (object, sn_name))
        return self.result_store.save({'result': object, 'sn_name': sn_name})

    def get_resolved_targets(self, root):
        while True:
            self.log.info('getting resolved targets for %s' % root)
            not_ended_count = self.targets.find({'root': root, 'result_id': {'$exists': False}}).count()
            self.log.info('not ended: %s' % not_ended_count)
            if not_ended_count > 0:
                time.sleep(STATUS_REFRESH_PERIOD_SEC)
                continue
            else:
                return [el for el in self.targets.find({'root': root, 'result_id': {'$exists': True}})]


    def get_target_result(self, root):
        self.log.info('getting resolved targets for %s' % root)
        targets = self.get_resolved_targets(root)
        result = {}
        for el in targets:
            result_el = self.result_store.find_one({'_id': el['result_id']})
            if result_el:
                result[result_el['sn_name']] = result_el['result']
        return result


class db_handler(object):
    def __init__(self):
        mongo_uri = 'mongodb://%s:%s@%s:%s/%s' % (db_user, db_password, db_host, db_port, db_name)
        try:
            self.engine = pymongo.MongoClient(mongo_uri)
        except ConnectionFailure as e:
            log.error('can not connect to database server')
            exit(-1)

        self.database = self.engine[db_name]

        self.messages = self.database['messages']
        self.users = self.database['users']


    def get_users(self):
        users = self.users.find()
        return [el for el in users]

    def get_user(self, id):
        user = self.users.find_one({'_id': id})
        return user