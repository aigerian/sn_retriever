from contrib.db_connector import db_handler

__author__ = '4ikist'

import json
import os
import logging

from contrib.connect import TwitterAPI, VkontakteAPI
import properties


log = logging.getLogger('main')


def mkdir(name):
    if not os.path.exists(name):
        os.mkdir(name)


def get_dump_to(command):
    comm_parts = command.split('/')
    mkdir('_dumps')
    os.chdir('_dumps')
    if len(comm_parts) > 1:
        mkdir(comm_parts[0])
        os.chdir(comm_parts[0])
        result = open(comm_parts[1], 'wb')
        os.chdir('..')
    else:
        result = open(comm_parts[0], 'wb')
    os.chdir('..')
    return result


def get_load_from(command):
    comm_dir = str(command).replace('/', os.path.sep)
    return open('_dumps%s%s' % (os.path.sep, comm_dir), 'rb')


if __name__ == '__main__':
    api = VkontakteAPI()

