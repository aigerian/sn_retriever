# coding=utf-8
from collections import defaultdict
from functools import partial
import datetime
import time
from itertools import chain
import html2text

from contrib.api.entities import APIUser, APIMessage, APIContentObject, APISocialObject
import re

__author__ = '4ikist'

rel_types_groups = ['member', 'admin', 'subscribe', 'request', 'invitation']
rel_types_users = ['friend', 'follower', 'like', 'comment', 'mentions']

iterated_counters = {'subscriptions': 200,
                     'followers': 1000,
                     'photos': 200,
                     'photo_comments': 100,
                     'videos': 200,
                     'wall': 100,
                     'notes': 100,
                     'groups': 1000}

unix_time = lambda x: datetime.datetime.fromtimestamp(int(x))
to_unix_time = lambda x: int(time.mktime(x.timetuple()))

def get_mentioned(text):
    """
    находит все идентификаторы в тексте такие: [id1234567|Имя Фамилия]
    :param text: в чем искать
    :return: список 1234567
    """
    if text is not None:
        return [el[3:-1] if 'id' in el else el[1:] for el in re.findall('\[id\d+\|?\:?', text)]
    return []


def _process_text_fields(data):
    for key in ['text', 'title', 'message', 'description', ]:
        if key in data and data.get(key) is not None:
            data[key] = html2text.html2text(data[key]).strip()


def _delete_fields_with_prefix(data, prefixes, l=True, r=False):
    to_replace = []
    for k, v in data.iteritems():
        if isinstance(k, (str, unicode)):
            for prefix in prefixes:
                if l and k.startswith(prefix):
                    to_replace.append(k)
                if r and k.endswith(prefix):
                    to_replace.append(k)
    for el in to_replace:
        data.pop(el, None)


class VK_APIUser(APIUser):
    def __init__(self, data_dict):
        data_dict['source'] = 'vk'
        data_dict['sn_id'] = data_dict.pop('uid', None) or data_dict.pop('id', None)
        if data_dict.get('bdate'):
            bdate = data_dict.get('bdate')
            if len(bdate) > 4:
                data_dict['bdate'] = datetime.datetime.strptime(bdate, '%d.%m.%Y')
            if len(bdate) < 6 and len(bdate) > 2:
                data_dict['bdate'] = datetime.datetime.strptime(bdate, '%d.%m')
        if data_dict.get('last_seen'):
            data_dict['last_visit'] = unix_time(data_dict['last_seen']['time'])
        if data_dict.get('counters'):
            counters = data_dict.get('counters')
            data_dict['followers_count'] = counters['followers']
            data_dict['friends_count'] = counters['friends']
        if 'screen_name' not in data_dict:
            data_dict['screen_name'] = data_dict.pop('domain', None) or data_dict.get('sn_id')
        data_dict['name'] = data_dict['first_name'] + ' ' + data_dict['last_name']
        super(VK_APIUser, self).__init__(data_dict)


class VK_APIMessage(APIMessage):
    def __init__(self, data_dict, created_at_format=None, comment_for=None, comment_id=None):
        data_dict['source'] = 'vk'
        if data_dict.get('user', None) is None:
            data_dict['user'] = {'sn_id': data_dict.pop('from_id', None) or data_dict.get('uid', None)}
        if not 'sn_id' in data_dict:
            data_dict['sn_id'] = data_dict.pop('cid', None) or data_dict.pop('id', None)
        if 'created_at' not in data_dict:
            data_dict['created_at'] = datetime.datetime.fromtimestamp(int(data_dict.pop('date')))
        if comment_for:
            data_dict['comment_for'] = comment_for
            data_dict['comment_id'] = comment_id or data_dict['comment_id']
        data_dict['user_id'] = data_dict['user']['sn_id']

        data_dict.pop('cid', None)
        data_dict.pop('online', None)
        data_dict.pop('uid', None)
        _process_text_fields(data_dict)
        super(VK_APIMessage, self).__init__(data_dict)

    @property
    def comment_id(self):
        return self.get('comment_id')


class VK_APIContentObject(APIContentObject):
    def __init__(self, data_dict):
        data_dict['source'] = 'vk'
        _process_text_fields(data_dict)
        super(VK_APIContentObject, self).__init__(data_dict)


class VK_APISocialObject(APISocialObject):
    def __init__(self, data_dict):
        data_dict['sn_id'] = data_dict.pop('id')
        data_dict['closed'] = data_dict.pop('is_closed', False)
        _delete_fields_with_prefix(data_dict, ('is_', 'photo_'), l=True, r=False)
        super(VK_APISocialObject, self).__init__(data_dict)


class ContentResult(object):
    def __init__(self):
        self._content = []
        # {from:{type1:[to1,to2,to3], type2:[to1,to2,to3]}}
        self._relations = defaultdict(partial(defaultdict, list))
        self._comments = []

    def __add_object(self, object_type, object_acc, object):
        if isinstance(object, list):
            object_acc.extend(object)
            return len(object)
        elif isinstance(object, object_type):
            object_acc.append(object)
            return 1

    def __concatenate_relations(self, other_relations):
        for from_, types_and_tos in other_relations.iteritems():
            if from_ in self._relations and len(self._relations[from_]):
                for type_, tos in other_relations[from_].iteritems():
                    if type_ not in rel_types_groups:
                        self._relations[from_][type_].extend(tos)
                    else:
                        tos = list(set(self._relations[from_][type_] + other_relations[from_][type_]))
                        self._relations[from_][type_] = tos
            else:
                self._relations[from_] = types_and_tos

    def __add_relation(self, relation):
        """
        Добавляет связь только если она имеет пользовательский тип либо если такой связи с групповым типом нет
        :param relation:
        :return:
        """
        if relation[1] in rel_types_groups:
            if relation[1] not in rel_types_groups and relation[2] in self._relations[relation[0]][relation[1]]:
                return
        self._relations[relation[0]][relation[1]].append(relation[2])

    def add_relations(self, relation_objects):
        """
        :param relation_objects:
        :return: count of added objects
        """
        if isinstance(relation_objects, list):
            for el in relation_objects:
                self.__add_relation(el)
        else:
            self.__add_relation(relation_objects)

    def add_comments(self, comments):
        return self.__add_object(APIMessage, self.comments, comments)

    def add_content(self, content_objects):
        return self.__add_object(APIContentObject, self.content, content_objects)

    def get_content_to_persist(self):
        return chain(self.comments, self.content)

    @property
    def content(self):
        return self._content

    @property
    def relations(self):
        result_acc = []
        for from_, types_and_tos in self._relations.iteritems():
            for type, to in types_and_tos.iteritems():
                for to_id in to:
                    result_acc.append((from_, type, to_id))
        return result_acc

    @property
    def comments(self):
        return self._comments

    def get_relations_with_type(self, relation_type, l=False, r=False):
        if not isinstance(relation_type, (list, tuple, set)):
            relation_type = [relation_type]
        result_acc = []
        for from_, types_and_tos in self._relations.iteritems():
            for type, to in types_and_tos.iteritems():
                if type in relation_type:
                    for to_ in to:
                        result_acc.append((from_, to_))
        if not l:
            returned_rels = [el[0] for el in result_acc]
        elif not r:
            returned_rels = [el[1] for el in result_acc]
        else:
            returned_rels = result_acc
        return returned_rels

    def __radd__(self, other):
        if isinstance(other, self.__class__) or isinstance(self, other.__class__):
            self._content += other._content
            self._comments += other._comments
            self.__concatenate_relations(other._relations)
            return self
        else:
            raise ValueError("+ operator with not ContentResult object")

    def __iadd__(self, other):
        return self.__radd__(other)

    def __add__(self, other):
        return self.__radd__(other)


if __name__ == '__main__':
    cr1 = ContentResult()
    cr1.add_relations([(1, 'member', 1), (1, 'member', 2), (2, 'comment', 1), (2, 'comment', 2)])
    cr2 = ContentResult()
    cr2.add_relations([(1, 'member', 1), (1, 'comment', 2), (2, 'member', 1), (2, 'comment', 1)])
    cr1+=cr2
    print cr1.relations

