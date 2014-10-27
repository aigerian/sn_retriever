# coding=utf-8
from Queue import Queue, Empty
import argparse

import sys
from datetime import datetime
import threading
from threading import Condition
from time import sleep

from contrib.api.vk.vk_entities import VK_APIUser, rel_types_groups
from contrib.api.vk.vk_execute import VK_API_Execute
from contrib.db.database_engine import Persistent
from contrib.utils import SocialDataStreamer
from properties import logger, vk_logins, vk_walker_threads_count
import properties


__author__ = '4ikist'

log = logger.getChild('walker_ttr')


def retrieving_objects_data(user_id, vk):
    if isinstance(user_id, (str, unicode)):
        if user_id.isdigit():
            el = int(user_id)
        else:
            user = vk.get_user_info(user_id)
            el = user.sn_id
    else:
        el = user_id
    if el > 0:
        result = vk.get_user_data(el)
    else:
        result = vk.get_group_data(el)
    return result


def persist_content_result(content_result, user_id, persist):
    """
    Сохраняет результат правильно. Сначала пользователей и их связи, а потом их данные. Ибо чтобы было привязывать к кому.
    Пользователей загружает скопом
    :param content_result: контент который сохраняем
    :param user_id: идентификатор пользователя которого сохраняем
    :return:
    """
    if content_result is None:
        return

    not_loaded_users = []
    not_loaded_groups = []

    def add_new_user(new_user_id):
        if new_user_id != user_id:
            is_loaded = persist.is_user_data_loaded(new_user_id)
            if isinstance(is_loaded, datetime) or is_loaded == True:
                return
            else:
                not_loaded_users.append(new_user_id)

    def add_new_group(group_id):
        if not persist.is_social_object_saved(group_id):
            not_loaded_groups.append(-abs(group_id))

    for from_id, types_and_tos in content_result.get_relations().iteritems():
        for rel_type, tos in types_and_tos.iteritems():
            for to in tos:
                if rel_type not in rel_types_groups:  # если связь не с группой
                    add_new_user(from_id), add_new_user(to)
                elif rel_type in rel_types_groups:
                    add_new_group(to)
            persist.save_relation(from_id, tos, rel_type)

    log.info("found %s related and not loaded users" % len(not_loaded_users))
    log.info("found %s related and not loaded groups" % len(not_loaded_groups))
    comments = content_result.comments
    persist.save_messages(comments)
    log.info('saved %s comments' % len(comments))

    content = content_result.content
    persist.save_content_objects(content)
    log.info('saved %s content objects' % len(content))

    return not_loaded_users + not_loaded_groups


def saving_objects_data(users_data, persist):
    user, result_object = users_data
    if isinstance(user, VK_APIUser):
        persist.save_user(user)
    else:
        persist.save_social_object(user)
    related_users = persist_content_result(result_object, user.sn_id, persist)
    return related_users


class UserRetriever(threading.Thread):
    def __init__(self, vk, ids_queue, data_queue, data_event, ids_events):
        super(UserRetriever, self).__init__()
        self.name = "retriever [%s]" % (vk.get_logins())
        self.vk = vk
        self.ids_queue = ids_queue
        self.data_queue = data_queue
        self.not_empty_data_queue = data_event
        self.not_empty_ids_queues = ids_events

    def run(self):
        trying_count = 5
        while 1:
            with self.not_empty_ids_queues:
                if not self.ids_queue.empty():
                    ids = self.ids_queue.get(block=False)
                    users_data = retrieving_objects_data(ids, self.vk)
                    log.info('%s was retrieved' % ids)
                    self.data_queue.put(users_data)
                else:
                    self.not_empty_ids_queues.wait(1)
                    trying_count -= 1
                    if trying_count < 1:
                        break
                    continue

            with self.not_empty_data_queue:
                self.not_empty_data_queue.notifyAll()


class UserSaver(threading.Thread):
    def __init__(self, persist, data_queue, ids_queue, data_event, ids_event, recursive=False):
        super(UserSaver, self).__init__()
        self.name = 'saver'
        self.persist = persist
        self.ids_queue = ids_queue
        self.data_queue = data_queue
        self.not_empty_data_queue = data_event
        self.not_empty_ids_queues = ids_event
        self.recursive = recursive

    def run(self):
        while 1:
            with self.not_empty_data_queue:
                if not self.data_queue.empty():
                    data = self.data_queue.get(block=False)
                    related_ids = saving_objects_data(data, self.persist)
                    if not related_ids or not isinstance(related_ids, list):
                        continue
                    if self.recursive:
                        for el in related_ids:
                            self.ids_queue.put(el)
                    else:
                        break
                else:
                    self.not_empty_data_queue.wait(1)
                    continue
            with self.not_empty_ids_queues:
                self.not_empty_ids_queues.notifyAll()


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--list', type=file, help='load list of user ids you must provide file of this list')
    parser.add_argument('-u', '--user', help='load user id')
    parser.add_argument('-r', '--recursive', help='will load social siblings of retrieved users', action='store_true')
    parser.add_argument('-v', '--visualise', help='will sending to gephi data', action='store_true')
    args = parser.parse_args()

    queue_data = Queue()
    queue_ids = Queue()
    is_ids_empty = threading.Condition()
    is_data_empty = threading.Condition()
    if args.list:
        with args.list as user_list:
            for line in user_list.xreadlines():
                queue_ids.put(line.strip)
    if args.user:
        queue_ids.put(args.user)

    count_processes = vk_walker_threads_count
    min_logins_at_process = len(vk_logins) / count_processes
    threads = []
    for el in xrange(count_processes):
        if el + 1 == count_processes:
            vk = VK_API_Execute(logins=vk_logins[el * min_logins_at_process:])
        else:
            vk = VK_API_Execute(logins=vk_logins[el * min_logins_at_process:(el + 1) * min_logins_at_process])
        p = UserRetriever(vk, queue_ids, queue_data, is_data_empty, is_ids_empty)
        p.start()
        threads.append(p)

    if args.visualise:
        persist = SocialDataStreamer()
    else:
        persist = Persistent()

    saver = UserSaver(persist, queue_data, queue_ids, is_data_empty, is_ids_empty, recursive=args.recursive)
    saver.start()
    threads.append(saver)
    for el in threads:
        print el
        el.join()



