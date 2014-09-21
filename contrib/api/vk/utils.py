# coding=utf-8
import datetime
from contrib.api.vk.vk_entities import ContentResult, VK_APIContentObject, VK_APIMessage, VK_APISocialObject, \
    rel_types_groups, \
    unix_time
import properties


__author__ = '4ikist'

log = properties.logger.getChild('vk_utils')


def persist_content_result(content_result, user_id, persist, vk):
    """
    Сохраняет результат правильно. Сначала пользователей и их связи, а потом их данные. Ибо чтобы было привязывать к кому.
    Пользователей загружает скопом
    :param content_result: контент который сохраняем
    :param user_id: идентификатор пользователя которого сохраняем
    :return:
    """
    output_users = []
    not_data_loaded_users = []
    not_loaded_users = []
    not_loaded_groups = []
    def add_new_user(new_user_id):
        if new_user_id != user_id:
            is_loaded = persist.is_user_data_loaded(new_user_id)
            if isinstance(is_loaded, datetime.datetime):
                return
            elif is_loaded == True:
                not_data_loaded_users.append(new_user_id)
            else:
                not_loaded_users.append(new_user_id)

    def add_new_group(group_id):
        if not persist.is_social_object_saved(group_id):
            not_loaded_groups.append(group_id)
    if content_result is None:
        return

    for from_id, rel_type, to_id in content_result.relations:
        if rel_type not in rel_types_groups:  # если связь не с группой
            add_new_user(from_id), add_new_user(to_id)
        elif rel_type in rel_types_groups:
            add_new_group(to_id)
        persist.save_relation(from_id, to_id, rel_type)
    log.info("found %s related and not loaded users" % len(not_loaded_users))
    log.info("found %s related and not data loaded users" % len(not_data_loaded_users))
    log.info("found %s related and not loaded groups" % len(not_loaded_groups))
    log.info("will load....")
    groups = vk.get_groups_info(not_loaded_groups)
    persist.save_object_batch(groups)

    users = vk.get_users_info(not_loaded_users)
    persist.save_object_batch(users)

    persist.save_object_batch(content_result.get_content_to_persist())
    return not_data_loaded_users+not_loaded_users


def _get_from_dict_part_of_key(dict, part_of_key):
    for k, v in dict.iteritems():
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
                                             'url': el['sizes'][-1]['src'] if el.get(
                                                 'sizes') else _get_from_dict_part_of_key(el, 'photo_'),
                                             'likes_count': el['likes']['count'],
                                             'photo_id': el['id'],
                                             'type': 'photo',
                                             'tags': el['tags']['count'] if el.get('tags') else None})
        content_result.add_content(photo_content)
    return content_result


def photo_comments_retrieve(photo_comments_elements, user_id):
    content_result = ContentResult()
    for el in photo_comments_elements:
        photo_comment = VK_APIMessage({'sn_id': 'comment_%s_for[%s_photo_%s]' % (el['id'], el['pid'], user_id),
                                       'text': el['text'],
                                       'created_at': unix_time(el['date']),
                                       'user': {'sn_id': el['from_id']},
                                       'likes_count': el['likes']['count']},
                                      comment_for={'sn_id': '%s_photo_%s' % (el['pid'], user_id), 'type': 'photo'},
                                      comment_id=el['id'])
        content_result.add_comments(photo_comment)
        content_result.add_relations((el['from_id'], 'comment', user_id))
    return content_result


def comments_retrieve(comments_elements, user_id, object_type, object_id):
    """
    Retrieving comments for some element
    :param comments_elements:
    :param user_id:
    :param object_type:
    :param object_id:
    :return:
    """
    content_result = ContentResult()
    for comment_data in comments_elements:
        comment = VK_APIMessage(
            {'sn_id': 'comment_%s_for[%s_%s_%s]' % (comment_data['id'], object_id, object_type, user_id),
             'text': comment_data['text'],
             'created_at': unix_time(comment_data['date']),
             'user': {'sn_id': comment_data['from_id']},
             'likes_count': comment_data['likes']['count']},
            comment_for={'sn_id': '%s_%s_%s' % (object_id, object_type, user_id), 'type': object_type},
            comment_id=comment_data['id'])
        if 'reply_to_user' in comment_data and 'reply_to_comment' in comment_data:
            comment['reply_to'] = {
                'sn_id': 'comment_%s_for[%s_%s_%s]' % (
                    comment_data['reply_to_comment'], object_id, object_type, user_id)}
        content_result.add_comments(comment)
        content_result.add_relations((comment_data['from_id'], 'comment', user_id))
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
             'post_id': wall_post_data['id'],
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
             'geo': wall_post_data.get('geo')
            })
        if 'attachments' in wall_post_data:#Аттачменты прибавляют и текстовых данных.
            wall_post['attachments'] = []
            for attachment in wall_post_data['attachments']:
                att_type = attachment.get('type')
                if att_type in ('photo', 'posted_photo', 'video', 'note', 'album'):
                    wall_post['attachments'].append({'type': att_type, 'sn_id': attachment[att_type]['id']})
                    wall_post['text'] += "%s %s" % (
                        attachment[att_type].get('title', ''), attachment[att_type].get('description', ''))
                elif att_type == 'link':
                    wall_post['attachments'].append({'type': att_type, 'url': attachment[att_type]['url']})
                    wall_post['text'] += "%s %s" % (
                        attachment[att_type].get('title', ''), attachment[att_type].get('description', ''))
                elif att_type == 'page':
                    wall_post['attachments'].append({'type': att_type, 'group_id': attachment[att_type]['group_id'],
                                                     'page_id': attachment[att_type]['id']})
                    wall_post['text'] += "%s %s" % (
                        attachment[att_type].get('title', ''), attachment[att_type].get('source', ''))
                elif att_type == 'poll':
                    wall_post['attachments'].append({'type': att_type, 'poll_id': attachment[att_type]['id']})
                    wall_post['text'] += attachment[att_type].get('question', '')
                elif att_type == 'doc':
                    wall_post['attachments'].append({'type': att_type, 'doc_id': attachment[att_type]['id']})
                    wall_post['text'] += attachment[att_type].get('title', '')
            wall_post['text'] = wall_post['text'].strip()
        if 'copy_history' in wall_post_data:
            repost = wall_post_data['copy_history'][0]
            wall_post['repost_of'] = {'id': repost['id'], 'user_id': repost['owner_id'],
                                      'sn_id': '%s_wall_post_%s' % (repost['id'], repost['owner_id'])}
        if 'reply_owner_id' in wall_post_data and 'reply_post_id' in wall_post_data:
            wall_post['repost_of'] = {'id': wall_post_data['reply_post_id'],
                                      'user_id': wall_post_data['reply_owner_id'],
                                      'sn_id': '%s_wall_post_%s' % (
                                          wall_post_data['reply_post_id'], wall_post_data['reply_owner_id'])}
        content_result.add_content(wall_post)
    return content_result


def note_retrieve(note_elements):
    content_result = ContentResult()
    for note_data in note_elements:
        note = VK_APIContentObject({'sn_id': '%s_note_%s' % (note_data['id'], note_data['owner_id']),
                                    'comments_count': note_data['comments'],
                                    'user': {'sn_id': note_data['owner_id']},
                                    'created_at': unix_time(note_data['date']),
                                    'note_id': note_data['id'],
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
        if el.get('is_admin'):
            content_result.add_relations((user.sn_id, 'admin', el['id']))
        elif el.get('is_member'):
            content_result.add_relations((user.sn_id, 'member', el['id']))
        else:
            content_result.add_relations((user.sn_id, 'subscribe', el['id']))
        page = VK_APISocialObject(el)
        content_result.add_content(page)
    return content_result