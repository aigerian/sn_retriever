from itertools import chain
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
    output_users = []
    posts, comments, related_users = retriever_function(user_id)
    persist.save_object_batch(posts)
    for comment in comments:
        if comment.user_id != user_id and not persist.get_user(sn_id=user_id):
            commented_user = vk.get_user(comment.user_id)
            persist.save_user(commented_user)
        persist.save_message(comment)

    for rel_type, related_users_ids in related_users.iteritems():
        for related_user_id in related_users_ids:
            persist.save_relation(user_id, related_user_id, rel_type)
        output_users.extend(related_users_ids)
    return output_users


def persist_all_user_data_and_retrieve_friends_ids(user_id):
    user = persist.get_user(sn_id=user_id) or vk.get_user(user_id)
    persist.save_user(user)
    related_users = []
    related_users.extend(persist_user_objects(vk.get_wall_posts, user.sn_id))
    related_users.extend(persist_user_objects(vk.get_photos, user.sn_id))
    related_users.extend(persist_user_objects(vk.get_videos, user.sn_id))
    return list(set(related_users))

    # cobs, coms, ru2 = vk.get_photos(user.sn_id)
    # for cob in cobs:
    # persist.save_content_object(cob)
    # for com in coms:
    # persist.save_message(com)
    # related_users.extend(ru2)
    # cobs, coms, ru3 = vk.get_videos(user.sn_id)
    # for cob in cobs:
    #     persist.save_content_object(cob)
    # for com in coms:
    #     persist.save_message(com)
    #
    # notes, comments = vk.get_notes(user.sn_id)
    # for note in chain(notes,comments):
    #    persist.save_message(note)
    #
    # groups = vk.get_groups(user_id)
    # for group in groups:
    #     persist.save_social_object(group)
    #     messages, content, ru4 = vk.get_group_data(group.sn_id)
    #     related_users.extend(ru4)


if __name__ == '__main__':
    persist_all_user_data_and_retrieve_friends_ids('266544674')




