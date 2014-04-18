# coding=utf-8

__author__ = '4ikist'

import logging
import os
import re

from pymorphy2 import MorphAnalyzer

from contrib.api.ttr import TTR_API
from contrib.timers import stopwatch

log = logging.getLogger('main')

morph = MorphAnalyzer()
excludes_classes = ['NPRO', 'PRED', 'PREP', 'CONJ', 'PRCL', 'INTJ']


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


url_reg = re.compile(
    '((http[s]?:\/\/)?(\w+)(-\w+)?(\.\w+)+(:\d+)?(\/[\w\d]*\.?[\w\d]*)*(\?[\w\d]*(=[\w\d]*)?(&[\w\d]*(=[\w\d]*)?)*)?(#[\w\d]*)?)')

split_reg = re.compile(u'[^a-zA-Z0-9а-яёА-ЯЁ@#\*_-]+')




@stopwatch
def test(n):
    for i in range(n):
        j = i * i
        x = []
        x.append(j)
        y = {}
        y[i] = x[:]


if __name__ == '__main__':
    ttr = TTR_API()
    result = [el['text'] for el in ttr.search(u'чеснок')]
    for el in result:
        log.info('[%s]' % el)
        processed = process_message(el)
        for token in processed:
            log.info('\ttoken start')
            for token_el in token:
                log.info('\t[%s]\t%s' % (token_el['type'], token_el['content']))
            log.info('\ttoken stop\n')
        log.info('----------------\n')
