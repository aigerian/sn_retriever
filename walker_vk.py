# coding=utf-8
from Queue import Empty
from datetime import datetime
from multiprocessing.queues import Queue
import sys
from contrib.api.vk import persist_content_result
from contrib.api.vk.vk_entities import rel_types_users

from contrib.api.vk.vk_execute import VK_API_Execute
from contrib.db.database_engine import Persistent
from properties import logger
import properties


__author__ = '4ikist'


log = logger.getChild('walker_ttr')



def persist_all_user_data_and_retrieve_related(vk, user_id, persist):
    saved_user = persist.get_user(sn_id=user_id)
    # Если пользователь уже сохранен и его данные сохранены  то возвращаем его пользовательские связи которые не были сохранены
    related_users_with_not_loaded_data = []
    if saved_user:
        related_users_with_not_loaded_data = [el for el in
                                              persist.get_related_users(user_id, rel_types_users, only_sn_ids=True,
                                                                        backwards=True) if
                                              persist.is_user_data_loaded(el) == 'not_data_load']
        if saved_user.get('data_load_at'):
            return related_users_with_not_loaded_data

    user, result_object = vk.get_user_data(user_id)
    log.info("user [%s (%s)] {%s} data was retrieved, saving..." % (user.screen_name, user.name, user.sn_id))
    persist.save_user(user)
    related_users = persist_content_result(result_object, user.sn_id, persist, vk)
    return related_users + related_users_with_not_loaded_data


class related_objects_queue(list):
    def __init__(self, queue=None):
        super(related_objects_queue, self).__init__()
        self.queue = queue or Queue()

    def append(self, value):
        self.queue.put(value)

    def next(self):
        try:
            return self.queue.get()
        except Empty:
            return None

    def add_to_found(self, som_list):
        for el in som_list:
            self.append(el)


def queue_user_loader(vk, queue):
    for el in queue:
        if el is None:
            break
        related = persist_all_user_data_and_retrieve_related(vk, el)
        queue.add_to_found(related)


def loading_user(start_user_id, vk, queue, persist):
    log.info("Starting... Retrieving user info for user: %s" % start_user_id)
    related_users = persist_all_user_data_and_retrieve_related(vk, start_user_id, persist)
    log.info("Started relations count: %s" % len(related_users))
    queue.add_to_found(set(related_users))
    while 1:
        for user_id in queue:
            if user_id is None:
                break
            log.info("Retrieving data for user %s" % user_id)
            _new_related_users = persist_all_user_data_and_retrieve_related(vk, user_id, persist)
            log.info("for user %s found %s relations" % (user_id, len(_new_related_users)))
            queue.add_to_found(set(_new_related_users))

        if len(related_users) == 0:
            break


from multiprocessing import Process, queues
import os


def info(title):
    print title


def load_users_data(start_user_id, count_processes=3):
    queue = related_objects_queue()
    logins = properties.vk_logins.values()
    processes = []
    persist = Persistent()
    for el in xrange(len(logins) / count_processes):
        vk = VK_API_Execute(
            logins=dict([(k, v) for k, v in enumerate(logins[el * count_processes:(el + 1) * count_processes])]))
        interested_user = queue.next() or start_user_id
        p = Process(target=loading_user, args=(interested_user, vk, queue, persist))
        p.start()
        processes.append(p)

    for el in processes:
        print 'wait %s' % el
        el.join()


if __name__ == '__main__':
    try:
        use_count_threads = sys.argv[2]
        start_user_identical = sys.argv[1]
    except:
        print "usage is:\nwalker_vk.py <start_user_id_or_screen_name> <count_threads>"
        print "now you forgot last parameter"
        sys.exit(0)
    load_users_data(start_user_identical, int(use_count_threads))


