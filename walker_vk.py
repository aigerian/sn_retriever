# coding=utf-8
from itertools import chain
import sys
from contrib.api.vk import VK_API
from contrib.db.database_engine import Persistent
from properties import logger

__author__ = '4ikist'

relation_type = 'friends'
start_user_screen_name = 'linoleum2k12'

persist = Persistent()

log = logger.getChild('walker_ttr')
vk = VK_API()


def persist_user_objects(retriever_function, user_id):
    """
    Извлекает объекты пользователя и создает в БД их отображение
    :param retriever_function:
    :param user_id:
    :return: список идентификаторов пользователей которые как-либо связанны с искомым (user_id)
    """
    output_users = []
    posts, comments, related_users = retriever_function(user_id)
    persist.save_object_batch(posts)
    for comment in comments:
        if comment.user_id != user_id and not persist.get_user(sn_id=user_id):
            commented_user = vk.get_user(comment.user_id)
            persist.save_user(commented_user)
        persist.save_message(comment)
        if 'likers' in comment:
            for comment_liker in comment.get('likers'):
                output_users.append(comment_liker)
                persist.save_relation(comment_liker, comment.user_id, 'likes')
        for mentioned_user in comment.get('mentioned'):
            output_users.append(mentioned_user)
            persist.save_relation(comment.user_id, mentioned_user, 'mentioned')

    for rel_type, related_users_ids in related_users.iteritems():
        for related_user_id in related_users_ids:
            if rel_type == 'mentioned':
                persist.save_relation(user_id, related_user_id, rel_type)
            else:
                persist.save_relation(related_user_id, user_id, rel_type)
        output_users.extend(related_users_ids)
    return output_users


def persist_user_relations(rel_function, user_id, rel_type, back=False):
    """
    Извлекает связи пользователя и делает отображение их в БД
    :param rel_function:
    :param user_id:
    :param rel_type:
    :param back:
    :return: возвращает идентификаторы пользователей связанных с искомым
    """
    rel_user_ids = []
    relations = rel_function(user_id)
    persist.save_object_batch(relations)
    for el in relations:
        if not back:
            persist.save_relation(user_id, el.sn_id, rel_type)
        else:
            persist.save_relation(el.sn_id, user_id, rel_type)
        rel_user_ids.append(el.sn_id)
    return rel_user_ids


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
        vk.get_group_data(group.sn_id)
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




