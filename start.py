# coding=utf-8
from threading import Thread

__author__ = '4ikist'

import os
import logging
import re
import time
import pymorphy2

from contrib.connect import VK_API, FB_API, TTR_API
from contrib.queue import QueueWorker, QueueServer


morph = pymorphy2.MorphAnalyzer()
re_words = re.compile(u'[^а-яёА-ЯЁa-zA-Z0-9]+')
excludes_classes = ['NPRO', 'PRED', 'PREP', 'CONJ', 'PRCL', 'INTJ']

log = logging.getLogger('main')


def mkdir(name):
    if not os.path.exists(name):
        os.mkdir(name)


def dump_to(command):
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


def load_from(command):
    comm_dir = str(command).replace('/', os.path.sep)
    return open('_dumps%s%s' % (os.path.sep, comm_dir), 'rb')


def process(message):
    log.info("process::: %s" % message)
    return {'ok': message}


if __name__ == '__main__':

    worker1 = QueueWorker(process)
    worker1.start()

    #server1 = QueueServer()
    #server2 = QueueServer()
    #
    #
    #
    #server1.send_message({'hi': 'from server 1 0'})
    #time.sleep(1)
    #server1.send_message({'hi': 'from server 1 1'})
    #time.sleep(1)
    #server1.send_message({'hi': 'from server 1 2'})
    #time.sleep(1)
    #server1.send_message({'hi': 'from server 1 3'})
    #time.sleep(1)
    #
    #server2.send_message({'hi': 'from server 2 0'})
    #time.sleep(1)
    #server2.send_message({'hi': 'from server 2 1'})
    #time.sleep(1)
    #server2.send_message({'hi': 'from server 2 2'})
    #time.sleep(1)
    #server2.send_message({'hi': 'from server 2 3'})
    #time.sleep(1)
    #server2.send_message({'hi': 'from server 2 4'})
    #time.sleep(1)
    #
    #server1.send_message({'hi': 'from server 1 4'})
    #time.sleep(1)
    #
    #server2.send_message({'hi': 'from server 2 5'})
    #time.sleep(1)
    #
    #server1.send_message({'hi': 'from server 1 5'})
    #time.sleep(1)
    #
    #
