__author__ = '4ikist'

import json
import os
import logging

from contrib.connect import ApiConnection
import properties

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(properties.log_file)
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s[%(levelname)s] %(name)s : %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

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
    api = ApiConnection()
    result = api.get_followers(screen_name='MedvedevRussia')
    json.dump(result, get_dump_to('followers/ids'))

    # command1 = 'statuses/user_timeline'
    # result = api.get(command1, get_dump_to(command1), ** {'screen_name': 'linoleum2k12'})
    # result = json.load(get_load_from(command1))
    #
    # for el in result:
    #     print el
    #     print el['text']
    #     print el['entities']
    #     print '-------------------------------------------'