#coding: utf-8
__author__ = '4ikist'

import logging

import pymongo
from pymongo.errors import ConnectionFailure

from properties import *


log = logging.getLogger('db_handler')


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

    def save_user(self, data):
        self.users.save(data)

    def save_message(self, data):
        self.messages.save(data)


if __name__ == '__main__':
    handler = db_handler()
    handler.save_message({'text': 'some_data'})
    handler.save_message({'text': 'some_data'})
    handler.save_message({'text': 'some_data'})
    handler.save_message({'text': 'some_data'})
    handler.save_user({'user': 'some_user'})
    handler.save_user({'user': 'some_user'})
    handler.save_user({'user': 'some_user'})
    handler.save_user({'user': 'some_user'})