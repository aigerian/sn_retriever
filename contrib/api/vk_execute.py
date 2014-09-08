# coding=utf-8
from contrib.api.vk import VK_API, ContentResult, VK_APIUser, VK_APIMessage, VK_APIContentObject, VK_APISocialObject, \
    unix_time
from contrib.api.entities import APISocialObject
import properties

__author__ = '4ikist'

social_objects_relations_type = ['member', 'admin', 'subscriber']


class VK_API_Execute(VK_API):
    def __init__(self):
        super(VK_API_Execute, self).__init__()

    def get_user_data(self, user_id):
        execute_code = """
            return {
            "user":API.users.get({"user_ids":%(user_id)s, "fields":%(user_fields)s}),
            "friends":API.friends.get({"user_id":%(user_id)s}),
            "subscriptions":API.users.getSubscriptions({"user_id":%(user_id)s, "extended":1, "count":200}),
            "followers":API.users.getFollowers({"user_id":%(user_id)s, "count":1000}),
            "photos":API.photos.getAll({"owner_id":%(user_id)s, "count":200, "photo_sizes":1,}),
            "photo_comments":API.photos.getAllComments({"owner_id":%(user_id)s, "need_likes":1, "count":100})
            "videos":API.video.get({"owner_id":%(user_id)s, "count":200}),
            "wall":API.wall.get({"owner_id":%(user_id)s, "count":100}),
            "notes":API.notes.get({"user_id":%(user_id)s, "count":100}),
            "groups":API.groups.get({"user_id":%(user_id)s, "count":1000})
            };
            """ % {'user_id': user_id, 'user_fields': properties.vk_user_fields}
        user_data = self.get('execute', **{'code': execute_code})
        content_result = ContentResult()
        user = VK_APIUser(user_data['user'][0])
        # связи пользователя
        content_result.add_relations([(el, 'following', user.sn_id) for el in user_data['followers']['items']])
        content_result.add_relations([(el, 'friend', user.sn_id) for el in user_data['friends']['items']])
        #его подписки (то что он читает)
        for el in user_data['subscriptions']['items']:
            page = VK_APISocialObject(el)
            content_result.add_content(page)
            if el['is_admin']:
                content_result.add_relations((user_id, 'admin', page.sn_id))
            elif el['is_member']:
                content_result.add_relations((user_id, 'member', page.sn_id))
            else:
                content_result.add_relations((user_id, 'subscribe', page.sn_id))
        #его фотографии и комментарии к ним
        content_result.add_content([VK_APIContentObject({'sn_id': '%s_photo_%s' % (el['id'], el['owner_id']),
                                                         'album': el['album_id'],
                                                         'user': {'sn_id': el['owner_id']},
                                                         'text': el['text'],
                                                         'created_at': unix_time(el['date']),
                                                         'url': el['sizes'][-1]['src'],
                                                         'likes_count': el['likes']['count'],
                                                         'photo_id':el['id'],
                                                         'type': 'photo'})
                                    for el in user_data['photos']['items']])
        content_result.add_comments([VK_APIMessage({'sn_id': '%s_comment_%s' % (el['id'], el['pid'])},
                                                   comment_for=el['pid'],
                                                   comment_id=el['id'])
                                     for el in user_data['photo_comments']['items']])
        #его видеозаписи
        content_result.add_content([VK_APIContentObject({'sn_id': '%s_video_%s' % (el['id'], el['owner_id']),
                                                         'user': {'sn_id': el['owner_id']},
                                                         'text': "%s %s" % (el['title'], el['description']),
                                                         'created_at': unix_time(el['date']),
                                                         'views_count': el['views'],
                                                         'comments_count': el['comments'],
                                                         'likes_count': el['likes']['count'],
                                                         'video_id':el['id'],
                                                         'type': 'video'})
                                    for el in user_data['videos']['items']])
        #его стена
        for wall_post_data in user_data['wall']['items']:
            wall_post = VK_APIContentObject(
                {'sn_id': '%s_wall_post_%s' % (wall_post_data['id'], wall_post_data['owner_id'])
                 'repost_count': wall_post_data['reposts']['count'],
                 'comments_count': wall_post_data['comments']['count'],
                 'likes_count': wall_post_data['likes']['count'],
                 'post_source': wall_post_data['post_source']['type'],
                 'text': wall_post_data['text'],
                 'post_type': wall_post_data['post_type'],
                 'type': 'wall_post',
                 'wall_post_id': wall_post_data['id'],
                 'user': {'sn_id': wall_post_data['owner_id']},
                 'created_at': unix_time(wall_post_data['']),
                })
            if 'attachments' in wall_post_data:
                wall_post['attachments'] = []
                for attachment in wall_post_data['attachments']:
                    wall_post['attachments'].append('%s_%s_%s'%(attachment['id'], attachment['type'], attachment['owner_id']))
            content_result.add_content(wall_post)





