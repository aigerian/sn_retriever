# coding=utf-8
__author__ = '4ikist'

import os
import logging
import re

import pymorphy2

from contrib.connect import VK_API, FB_API, Ttr_API

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


if __name__ == '__main__':
    api = Ttr_API()
    result = api.get_user_timeline(screen_name='mongodbinc')
    print result

