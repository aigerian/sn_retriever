# coding=utf-8
from contrib.api.vk import VK_API, ContentResult, VK_APIUser, VK_APIMessage, VK_APIContentObject, VK_APISocialObject, \
    unix_time, get_mentioned
from contrib.api.entities import APISocialObject
import properties

__author__ = '4ikist'

social_objects_relations_type = ['member', 'admin', 'subscriber']

class ContentResultIntelligentRelations(ContentResult):
    """
    Класс объект которого при сохранении комментариев или контента смотрит
    на текст и добавляет упомянутых пользователей в связи
    """
    def __init__(self):
        super(ContentResultIntelligentRelations, self).__init__()

    def add_comments(self, comments):
        count_before = len(self.comments)
        super(ContentResultIntelligentRelations,self).add_comments(comments)
        count_after = len(self.comments)
        for added_comment in self.comments[count_before-count_after:]:
            self.add_relations([(added_comment['user']['sn_id'],'mentions',el)
                                for el in get_mentioned(added_comment['text'])])

    def add_content(self, content_objects):
        count_before = len(self.content)
        super(ContentResultIntelligentRelations,self).add_content(content_objects)
        count_after = len(self.content)
        for added_content in self.content[count_before-count_after:]:
            self.add_relations([(added_content['user']['sn_id'],'mentions',el)
                                for el in get_mentioned(added_content['text'])])



class VK_API_Execute(VK_API):
    def __init__(self):
        super(VK_API_Execute, self).__init__()

    def get_user_data(self, user_id):
        execute_code = ("""
            var user = API.users.get({"user_ids":"%(user_id)s", "fields":"%(user_fields)s"})[0];
            return {
            "user":user,
            "friends":API.friends.get({"user_id":user.id}),
            "subscriptions":API.users.getSubscriptions({"user_id":user.id, "extended":1, "count":200}),
            "followers":API.users.getFollowers({"user_id":user.id, "count":1000}),
            "photos":API.photos.getAll({"owner_id":user.id, "count":200, "photo_sizes":1,}),
            "photo_comments":API.photos.getAllComments({"owner_id":user.id, "need_likes":1, "count":100}),
            "videos":API.video.get({"owner_id":user.id, "count":200}),
            "wall":API.wall.get({"owner_id":user.id, "count":100}),
            "notes":API.notes.get({"user_id":user.id, "count":100}),
            "groups":API.groups.get({"user_id":user.id, "count":1000})
            };
            """ % {'user_id': user_id, 'user_fields': properties.vk_user_fields}).strip().replace('\n','')
        user_data = self.get('execute', **{'code': execute_code})
        content_result = ContentResult()
        user = VK_APIUser(user_data['user'])
        # связи пользователя
        content_result.add_relations([(el, 'following', user.sn_id) for el in user_data['followers']['items']])
        content_result.add_relations([(el, 'friend', user.sn_id) for el in user_data['friends']])
        # его подписки (то что он читает)
        if user_data['subscriptions']:
            user['subscriptions_count'] = user_data['subscriptions']['count']
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
        if user_data['photos']:
            user['photos_count'] = user_data['photos']['count']
            content_result.add_content([VK_APIContentObject({'sn_id': '%s_photo_%s' % (el['id'], el['owner_id']),
                                                             'album': el['album_id'],
                                                             'user': {'sn_id': el['owner_id']},
                                                             'text': el['text'],
                                                             'created_at': unix_time(el['date']),
                                                             'url': el['sizes'][-1]['src'],
                                                             'likes_count': el['likes']['count'],
                                                             'photo_id': el['id'],
                                                             'type': 'photo'})
                                        for el in user_data['photos']['items']])
            if user_data['photos_comments']:
                content_result.add_comments([VK_APIMessage({'sn_id': '%s_comment_%s' % (el['id'], el['pid'])},
                                                           comment_for=el['pid'],
                                                           comment_id=el['id'])
                                             for el in user_data['photo_comments']['items']])
        #его видеозаписи
        if user_data['videos']:
            user['videos_count'] = user_data['videos']['count']
            content_result.add_content([VK_APIContentObject({'sn_id': '%s_video_%s' % (el['id'], el['owner_id']),
                                                             'user': {'sn_id': el['owner_id']},
                                                             'text': "%s %s" % (el['title'], el['description']),
                                                             'created_at': unix_time(el['date']),
                                                             'views_count': el['views'],
                                                             'comments_count': el['comments'],
                                                             'likes_count': el['likes']['count'],
                                                             'video_id': el['id'],
                                                             'type': 'video'})
                                        for el in user_data['videos']['items']])
        #его стена
        if user_data['wall']:
            user['wall_post_count'] = user_data['wall']['count']
            for wall_post_data in user_data['wall']['items']:
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
                        wall_post['attachments'].append(
                            '%s_%s_%s' % (attachment['id'], attachment['type'], attachment['owner_id']))
                if 'copy_history' in wall_post_data:
                    repost = wall_post_data['copy_history'][0]
                    wall_post['repost_of'] = "%s_wall_post_%s" % (repost['id'], repost['owner_id'])
                content_result.add_content(wall_post)
        #его записки
        if user_data['notes']:
            user['notes_count']=user_data['notes']['count']
            for note_data in user_data['notes']['items']:
                note = VK_APIContentObject({'sn_id':'%s_note_%s'%(note_data['id'], note_data['owner_id']),
                                            'comments_count':note_data['comments'],
                                            'user':{'sn_id':note_data['owner_id']},
                                            'created_at':unix_time(note_data['date']),
                                            'text':'%s %s'%(note_data['title'],note_data['title']),
                                            })
                content_result.add_content(note)
        #его групы
        groups = []
        if user_data['groups']:
            user['groups_count'] = user_data['groups']['count']
            groups = user_data['groups']['items']
        return user, content_result, groups


if __name__ == '__main__':
    vk = VK_API_Execute()
    user, content_result, groups = vk.get_user_data(266544674)
    print user
    print content_result
    print groups
