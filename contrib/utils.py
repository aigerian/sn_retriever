# coding=utf-8
from contrib.db.database_engine import Persistent
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


import json
import requests
from properties import gephi_master_url


class GephiStreamer(object):
    def __init__(self):
        self.log = properties.logger.getChild('gephi_streamer')
        self.nodes = {}
        self.edges = {}

    def __send(self, data):
        to_send = json.dumps(data)
        try:
            requests.post(gephi_master_url, data=to_send)
        except IOError as e:
            self.log.error('can not connect to gephi')

    def add_node(self, node_data):
        """
        Must be object with sn_id and name properties
        :param node_data:
        :return:
        """
        if node_data.sn_id not in self.nodes:
            self.__send({'an': {
                node_data.sn_id: {'label': node_data.get('screen_name', ''),
                                  'timeline_count': node_data.get('statuses_count', 0),
                                  'friends_count': node_data.get('friends_count', 0),
                                  'followers_count': node_data.get('followers_count', 0)}}})
        elif self.nodes[node_data.sn_id] is None:
            self.__send({'cn': {
                node_data.sn_id: {'label': node_data.get('screen_name', ''),
                                  'timeline_count': node_data.get('statuses_count', 0),
                                  'friends_count': node_data.get('friends_count', 0),
                                  'followers_count': node_data.get('followers_count', 0),
                                  'not_loaded': False}}})
        self.nodes[node_data.sn_id] = node_data

    def add_relation(self, from_node_id, to_node_id, relation_type):
        """
        sending to gephi master graph streamer two nodes and one edge
        :param from_node: {identifier:{'label':..., 'weight':...}}
        :param to_node: {identifier:{'label':..., 'weight':...}}
        :return:
        """
        if from_node_id not in self.nodes:
            self.__send({'an': {from_node_id: {'label': from_node_id, 'not_loaded': True}}})
            self.nodes[from_node_id] = None
        if to_node_id not in self.nodes:
            self.__send({'an': {to_node_id: {'label': to_node_id, 'not_loaded': True}}})
            self.nodes[to_node_id] = None

        edge_id = "%s_%s" % (from_node_id, to_node_id)
        saved = self.edges.get(edge_id)
        if saved is None:
            self.edges[edge_id] = 1
            self.__send(
                {'ae': {
                    edge_id: {'source': from_node_id,
                              'target': to_node_id,
                              'directed': True,
                              'weight': self.edges[edge_id],
                              'label': relation_type
                              }
                }})
        else:
            saved += 1
            self.edges[edge_id] = saved
            self.__send({'ce': {edge_id: {'weight': saved}}})


class SocialDataStreamer(Persistent):
    def __init__(self, truncate=False, host=None, port=None, name=None, r_host=None, r_port=None, r_dbnum=0):
        self.streamer = GephiStreamer()
        super(SocialDataStreamer, self).__init__(truncate, host, port, name, r_host, r_port, r_dbnum)

    def save_relation(self, from_id, to_id, relation_type):
        super(SocialDataStreamer, self).save_relation(from_id, to_id, relation_type)
        if isinstance(to_id, list):
            for to_el in to_id:
                self.streamer.add_relation(from_id, to_el, relation_type)
        else:
            self.streamer.add_relation(from_id, to_id, relation_type)

    def save_user(self, user):
        super(SocialDataStreamer, self).save_user(user)
        self.streamer.add_node(user)


if __name__ == '__main__':
    sds = SocialDataStreamer()
    sds.save_relation(1, 2, 'test')
    sds.save_relation(1, 3, 'test')
    sds.save_relation(2, 1, 'test')
    sds.save_relation(3, 1, 'test')
    sds.save_relation(4, 1, 'test')
    sds.save_relation(5, 1, 'test')
    from contrib.api.entities import APIUser

    sds.save_user(
        APIUser({'sn_id': 1, 'friends_count': 1, 'statuses_count': 1, 'followers_count': 1, 'screen_name': 'one'}))
    sds.save_user(
        APIUser({'sn_id': 2, 'friends_count': 1, 'statuses_count': 1, 'followers_count': 1, 'screen_name': 'two'}))
    sds.save_user(
        APIUser({'sn_id': 3, 'friends_count': 1, 'statuses_count': 1, 'followers_count': 1, 'screen_name': 'three'}))
    sds.save_user(
        APIUser({'sn_id': 4, 'friends_count': 1, 'statuses_count': 1, 'followers_count': 1, 'screen_name': 'four'}))
    sds.save_user(
        APIUser({'sn_id': 5, 'friends_count': 1, 'statuses_count': 1, 'followers_count': 1, 'screen_name': 'five'}))