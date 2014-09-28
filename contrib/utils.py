# coding=utf-8
import datetime
import properties

__author__ = '4ikist'
import re

url_reg = re.compile(
    '((http[s]?:\/\/)?(\w+)(-\w+)?(\.\w+)+(:\d+)?(\/[\w\d]*\.?[\w\d]*)*(\?[\w\d]*(=[\w\d]*)?(&[\w\d]*(=[\w\d]*)?)*)?(#[\w\d]*)?)')

split_reg = re.compile(u'[^a-zA-Z0-9а-яёА-ЯЁ@#\*_-]+')


def process_message(message):
    worked_copy = message[:]
    urls = [el[0] for el in url_reg.findall(message)]
    c = 0
    urls_hash = {}
    for url in urls:
        worked_copy = worked_copy.replace(url, ' url_%s ' % c)
        urls_hash[c] = url
        c += 1
    tokens = [el for el in split_reg.split(worked_copy) if len(el.strip()) >= 1]
    result = []
    for token in tokens:
        if token.startswith('url'):
            result.append({'content': urls_hash[int(token[-1])], 'type': 'url'})
        elif token.startswith('@'):
            result.append({'content': token[1:], 'type': 'mention'})
        elif token.startswith('#'):
            result.append({'content': token[1:], 'type': 'hash_tag'})
        else:
            result.append({'content': token, 'type': 'word'})

    return result


