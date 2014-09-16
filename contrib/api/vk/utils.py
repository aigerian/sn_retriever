# coding=utf-8
import datetime
from contrib.api.vk.vk_entities import ContentResult, VK_APIContentObject, VK_APIMessage, VK_APISocialObject, rel_types_groups, \
    unix_time


__author__ = '4ikist'


def persist_content_result(content_result, user_id, persist, vk):
    """
    Сохраняет результат правильно. Сначала пользователей и их связи, а потом их данные.
    Пользователей загружает скопом
    :param content_result: контент который сохраняем
    :param user_id: идентификатор пользователя которого сохраняем

    :return:
    """
    output_users = []
    not_loaded_users = []

    def add_new_user(new_user_id):
        if new_user_id != user_id:
            if not persist.is_loaded(new_user_id):
                not_loaded_users.append(new_user_id)
            output_users.append(new_user_id)
    if content_result is None:
        return

    for from_id, rel_type, to_id in content_result.relations:
        if rel_type not in rel_types_groups:  # если связь не с группой
            add_new_user(from_id), add_new_user(to_id)
        persist.save_relation(from_id, rel_type, to_id)

    users = vk.get_users_info(not_loaded_users)
    persist.save_object_batch(users)
    persist.save_object_batch(content_result.get_content_to_persist())
    return output_users

def _get_from_dict_part_of_key(dict, part_of_key):
    for k,v in dict.iteritems():
        if part_of_key in k:
            return v

def photo_retrieve(photo_elements):
    content_result = ContentResult()
    for el in photo_elements:
        photo_content = VK_APIContentObject({'sn_id': '%s_photo_%s' % (el['id'], el['owner_id']),
                                             'album': el['album_id'],
                                             'user': {'sn_id': el['owner_id']},
                                             'text': el['text'],
                                             'created_at': unix_time(el['date']),
                                             'url': el['sizes'][-1]['src'] if el.get('sizes') else _get_from_dict_part_of_key(el,'photo_') ,
                                             'likes_count': el['likes']['count'],
                                             'photo_id': el['id'],
                                             'type': 'photo',
                                             'tags':el['tags']['count']})
        content_result.add_content(photo_content)
    return content_result


def photo_comments_retrieve(photo_comments_elements):
    content_result = ContentResult()
    for el in photo_comments_elements:
        photo_comment = VK_APIMessage({'sn_id': '%s_comment_%s' % (el['id'], el['pid']),
                                       'text': el['text'],
                                       'created_at': unix_time(el['date']),
                                       'user': {'sn_id': el['from_id']},
                                       'likes_count': el['likes']['count']},
                                      comment_for=el['pid'],
                                      comment_id=el['id'])
        content_result.add_comments(photo_comment)
    return content_result


def video_retrieve(video_elements):
    content_result = ContentResult()
    for el in video_elements:
        video_content = VK_APIContentObject({'sn_id': '%s_video_%s' % (el.get('id') or el.get('vid'), el['owner_id']),
                                             'user': {'sn_id': el['owner_id']},
                                             'text': "%s %s" % (el['title'], el['description']),
                                             'created_at': unix_time(el['date']),
                                             'views_count': el['views'],
                                             'comments_count': el['comments'],
                                             'likes_count': el['likes']['count'] if el.get('likes') else 0,
                                             'video_id': el['id'],
                                             'type': 'video'})
        content_result.add_content(video_content)
    return content_result


def wall_retrieve(wall_elements):
    content_result = ContentResult()
    for wall_post_data in wall_elements:
        wall_post = VK_APIContentObject(
            {'sn_id': '%s_wall_post_%s' % (wall_post_data['id'], wall_post_data['owner_id']),
             'repost_count': wall_post_data['reposts']['count'],
             'comments_count': wall_post_data['comments']['count'],
             'likes_count': wall_post_data['likes']['count'],
             'post_source': wall_post_data['post_source']['type'],
             'text': wall_post_data['text'],
             'post_type': wall_post_data['post_type'],
             'type': 'wall_post',
             'wall_post_id': wall_post_data['id'],
             'user': {'sn_id': wall_post_data['owner_id']},
             'created_at': unix_time(wall_post_data['date']),
            })
        if 'attachments' in wall_post_data:
            wall_post['attachments'] = []
            for attachment in wall_post_data['attachments']:
                if attachment['type'] == 'link':
                    wall_post['attachments'].append({attachment['type']: attachment[attachment['type']]['url']})
                elif 'list' not in attachment['type']:
                    wall_post['attachments'].append(
                        '%s_%s_%s' % (attachment[attachment['type']]['id'], attachment['type'],
                                      attachment[attachment['type']]['owner_id']))
                else:
                    wall_post['attachments'].append({attachment['type']: attachment[attachment['type']]})
        if 'copy_history' in wall_post_data:
            repost = wall_post_data['copy_history'][0]
            wall_post['repost_of'] = "%s_wall_post_%s" % (repost['id'], repost['owner_id'])
        content_result.add_content(wall_post)
    return content_result

def note_retrieve(note_elements):
    content_result = ContentResult()
    for note_data in note_elements:
        note = VK_APIContentObject({'sn_id': '%s_note_%s' % (note_data['id'], note_data['owner_id']),
                                        'comments_count': note_data['comments'],
                                        'user': {'sn_id': note_data['owner_id']},
                                        'created_at': unix_time(note_data['date']),
                                        'text': '%s %s' % (note_data['title'], note_data['title']),
            })
        content_result.add_content(note)
    return content_result

def group_retrieve(group_elements, user):
    content_result = ContentResult()
    for el in group_elements:
        group = VK_APISocialObject(el)
        content_result.add_content(group)
        content_result.add_relations((user.sn_id, 'member', group.sn_id))
    return content_result

def subscriptions_retrieve(subscription_elements, user):
    content_result = ContentResult()
    for el in subscription_elements:
        if el['is_admin']:
                content_result.add_relations((user.sn_id, 'admin', el['id']))
        elif el['is_member']:
            content_result.add_relations((user.sn_id, 'member', el['id']))
        else:
            content_result.add_relations((user.sn_id, 'subscribe', el['id']))
        page = VK_APISocialObject(el)
        content_result.add_content(page)
    return content_result