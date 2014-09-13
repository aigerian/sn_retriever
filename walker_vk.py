# coding=utf-8
from datetime import datetime
from itertools import chain
import sys
from contrib.api.vk_execute import VK_API_Execute, social_objects_relations_type, user_relations
import html2text
from contrib.api.vk import VK_API
from contrib.db.database_engine import Persistent
from properties import logger
import properties

__author__ = '4ikist'

persist = Persistent()

log = logger.getChild('walker_ttr')
vk = VK_API_Execute()


def persist_content_result(content_result, user_id):
    """
    Сохраняет результат правильно. Сначала пользователей и их связи, а потом их данные.
    Пользователей загружает скопом
    :param content_result:
    :return:
    """
    output_users = []
    not_loaded_users = []

    def add_new_user(new_user_id):
        if new_user_id != user_id:
            if not persist.is_loaded(new_user_id):
                not_loaded_users.append(new_user_id)
                output_users.append(new_user_id)

    for from_id, rel_type, to_id in content_result.relations:
        if rel_type not in social_objects_relations_type: #если связь не с группой
            add_new_user(from_id), add_new_user(to_id)
        persist.save_relation(from_id, rel_type, to_id)

    users = vk.get_users(not_loaded_users)
    persist.save_object_batch(users)

    persist.save_object_batch(content_result.get_content_to_persist())
    return output_users


def persist_all_user_data_and_retrieve_related(user_id):
    saved_user = persist.get_user(sn_id=user_id)
    if saved_user and 'data_load_at' in saved_user and (
                datetime.now() - saved_user['data_load_at']).total_seconds() < properties.update_iteration_time:
        return reduce(lambda x, y: x.extend(y),
                      [persist.get_related_users(saved_user.sn_id, relation_type=el, only_sn_ids=True) for el in
                       user_relations],
            [])
    user, result_object = vk.get_user_data(user_id)
    user['data_load_at'] = datetime.now()
    persist.save_user(user)
    related_users = persist_content_result(result_object, user.sn_id)
    return related_users


if __name__ == '__main__':
    try:
        start_user_id = sys.argv[1]
    except:
        print "usage is:\nwalker_vk.py <start_user_id_or_screen_name>"
        print "now you forgot last parameter"
        sys.exit(0)
    log.info("Starting... Retrieving user info for user: %s" % start_user_id)
    related_users = persist_all_user_data_and_retrieve_related(start_user_id)
    while 1:
        new_related_users = []
        for user_id in related_users:
            log.info("Retrieving info for user %s" % user_id)
            new_related_users.extend(persist_all_user_data_and_retrieve_related(user_id))
        related_users = list(set(new_related_users))





