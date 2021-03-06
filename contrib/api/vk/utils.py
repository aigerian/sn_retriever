# coding=utf-8
from contrib.api.vk.vk_entities import ContentResult, VK_APIContentObject, VK_APIMessage, VK_APISocialObject, unix_time

import properties


__author__ = '4ikist'

log = properties.logger.getChild('vk_utils')


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        else:
            cls._instances[cls].__init__(*args, **kwargs)
        return cls._instances[cls]


def _get_from_dict_part_of_key(dict, part_of_key):
    for k, v in dict.iteritems():
        if part_of_key in k:
            return v


def photo_retrieve(photo_elements):
    content_result = ContentResult()
    for el in photo_elements:
        owner_id = el['owner_id']
        photo_content = VK_APIContentObject({'sn_id': '%s_photo_%s' % (el['id'], owner_id),
                                             'album': el['album_id'],
                                             'owner': {'sn_id': owner_id, 'type': 'user' if owner_id > 0 else 'group'},
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
                                       'owner': {'sn_id': el['from_id'], 'type': 'user'},
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
             'owner': {'sn_id': comment_data['from_id'], 'type': 'user'},
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
        owner_id = el['owner_id']
        video_content = VK_APIContentObject({'sn_id': '%s_video_%s' % (el.get('id') or el.get('vid'), owner_id),
                                             'owner': {'sn_id': owner_id, 'type': 'user' if owner_id > 0 else 'group'},
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
        owner_id = wall_post_data['owner_id']
        wall_post = VK_APIContentObject(
            {'sn_id': '%s_wall_post_%s' % (wall_post_data['id'], owner_id),
             'post_id': wall_post_data['id'],
             'repost_count': wall_post_data['reposts']['count'],
             'comments_count': wall_post_data['comments']['count'],
             'likes_count': wall_post_data['likes']['count'],
             'post_source': wall_post_data['post_source']['type'],
             'text': wall_post_data['text'],
             'post_type': wall_post_data['post_type'],
             'type': 'wall_post',
             'wall_post_id': wall_post_data['id'],
             'owner': {'sn_id': owner_id, 'type': 'user' if owner_id > 0 else 'group'},
             'created_at': unix_time(wall_post_data['date']),
             'geo': wall_post_data.get('geo')
            })
        if 'attachments' in wall_post_data:  # Аттачменты прибавляют и текстовых данных.
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
                                    'owner': {'sn_id': note_data['owner_id'], 'type': 'user'},
                                    'created_at': unix_time(note_data['date']),
                                    'note_id': note_data['id'],
                                    'text': '%s %s' % (note_data['title'], note_data['title']),
        })
        content_result.add_content(note)
    return content_result


def board_retrieve(board_elements, group_id):
    content_result = ContentResult()
    for el in board_elements:
        board = VK_APIContentObject({
            'sn_id': el['id'],
            'text': el['title'],
            'created': unix_time(el['created']),
            'updated': unix_time(el['updated']),
            'comments_count': el['comments'],
            'closed': el['is_closed'],
            'type': 'board'
        })
        content_result.add_content(board)
        content_result.add_relations((el['created_by'], 'board_create', group_id))
        content_result.add_relations((el['updated_by'], 'board_comment', group_id))
    return content_result


def group_retrieve(group_elements, user_id):
    content_result = ContentResult()
    for el in group_elements:
        group = VK_APISocialObject(el)
        content_result.add_group(group)
        content_result.add_relations((user_id, 'member', group.sn_id))
    return content_result

def members_retrieve(members_object, group_id):
    content_result = ContentResult()
    for member_id in members_object.get('items', []):
        content_result.add_relations((member_id, 'member', group_id))
    return content_result

def subscriptions_retrieve(subscription_elements, user_id):
    content_result = ContentResult()
    for el in subscription_elements:
        type = el.get('type')
        if type == 'profile':
            content_result.add_relations((user_id, 'follower', el['id']))
        else:
            if el.get('is_admin'):
                content_result.add_relations((user_id, 'admin', el['id']))
            elif el.get('is_member'):
                content_result.add_relations((user_id, 'member', el['id']))
            else:
                content_result.add_relations((user_id, 'subscribe', el['id']))
            page = VK_APISocialObject(el)
            content_result.add_group(page)
    return content_result