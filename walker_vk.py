# coding=utf-8
from itertools import chain
import sys
import html2text
from contrib.api.vk import VK_API
from contrib.db.database_engine import Persistent
from properties import logger

__author__ = '4ikist'

persist = Persistent()

log = logger.getChild('walker_ttr')
vk = VK_API()


def persist_content_result(content_result):
    """
    Сохраняет результат правильно. Сначала пользователей и их связи, а потом их данные.
    :param content_result:
    :return:
    """
    output_users = []

    def add_new_user(new_user_id):
        if new_user_id != user_id:
            new_user = vk.get_user(new_user_id)
            persist.save_user(new_user)
            output_users.append(new_user_id)

    for from_id, rel_type, to_id in content_result.relations:
        add_new_user(from_id), add_new_user(to_id)
        persist.save_relation(from_id, rel_type, to_id)

    persist.save_object_batch(content_result.get_content_to_persist())
    return output_users


def persist_user_objects(retriever_function, user_id):
    """
    Извлекает объекты пользователя и создает в БД их отображение
    :param retriever_function:
    :param user_id:
    :return: список идентификаторов пользователей которые как-либо связанны с искомым (user_id)
    """

    contentResult = retriever_function(user_id)
    return persist_content_result(contentResult)


def persist_all_user_data_and_retrieve_related(user_id):
    user = persist.get_user(sn_id=user_id, screen_name=user_id) or vk.get_user(user_id)
    persist.save_user(user)
    related_users = []
    # related_users.extend(persist_user_objects(vk.get_wall_posts, user.sn_id))
    # related_users.extend(persist_user_objects(vk.get_photos, user.sn_id))
    # related_users.extend(persist_user_objects(vk.get_videos, user.sn_id))
    # related_users.extend(persist_user_objects(vk.get_notes, user.sn_id))
    # related_users.extend(persist_user_relations(vk.get_followers, user.sn_id, 'follower', back=True))
    # related_users.extend(persist_user_relations(vk.get_subscriptions, user.sn_id, 'follower'))
    # related_users.extend(persist_user_relations(vk.get_friends, user.sn_id, 'friend'))
    groups = vk.get_groups(user.sn_id)
    for group in groups:
        gd_result = vk.get_group_data(group.sn_id)
        related_users.extend(persist_content_result(gd_result))
    return list(set(related_users))


if __name__ == '__main__':
    try:
        start_user_id = sys.argv[1]
    except:
        print "usage is:\nwalker_vk.py <start_user_id_or_screen_name>"
        print "now you forgot last parameter"
        sys.exit(0)

    related_users = persist_all_user_data_and_retrieve_related(start_user_id)
    for user_id in related_users:
        persist_all_user_data_and_retrieve_related(user_id)




