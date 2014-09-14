# coding=utf-8
from datetime import datetime
from contrib.api.vk.vk import VK_API, ContentResult, VK_APIUser, VK_APIMessage, VK_APIContentObject, VK_APISocialObject, get_mentioned
from contrib.api.vk.utils import photo_retrieve, photo_comments_retrieve, video_retrieve, wall_retrieve, note_retrieve, \
    group_retrieve, subscriptions_retrieve
import properties

__author__ = '4ikist'


class ContentResultIntelligentRelations(ContentResult):
    """
    Класс объект которого при сохранении комментариев или контента смотрит
    на текст и добавляет упомянутых пользователей в связи, а также
    """

    def __init__(self, user_id):
        super(ContentResultIntelligentRelations, self).__init__()
        self.user_id = user_id


    def add_comments(self, comments):
        count_added = super(ContentResultIntelligentRelations, self).add_comments(comments)
        for added_comment in self.comments[-count_added:]:
            if added_comment.get('text'):
                self.add_relations([(added_comment['user']['sn_id'], 'mentions', el)
                                    for el in get_mentioned(added_comment['text'])])
                self.add_relations((added_comment['user']['sn_id'], 'comment', self.user_id))

    def add_content(self, content_objects):
        count_added = super(ContentResultIntelligentRelations, self).add_content(content_objects)
        for added_content in self.content[-count_added:]:
            if added_content.get('user') and added_content.get('text'):
                self.add_relations([(added_content['user']['sn_id'], 'mentions', el)
                                    for el in get_mentioned(added_content.get('text'))])


class VK_API_Execute(VK_API):
    def __init__(self):
        super(VK_API_Execute, self).__init__()

    def get_user_data(self, user_id):
        """
        Извлекает основные данные пользователя. Комментарии только к фотографиям.
        Код на стороне контакта:
        var f_user = API.users.get({"user_ids":"%(user_id)s", "fields":"%(user_fields)s"})[0];
                return {
                "user":f_user,
                "friends":API.friends.get({"user_id":f_user.id}),
                "subscriptions":API.users.getSubscriptions({"user_id":f_user.id, "extended":1, "count":200}),
                "followers":API.users.getFollowers({"user_id":f_user.id, "count":1000}),
                "photos":API.photos.getAll({"owner_id":f_user.id, "count":200, "photo_sizes":1,"extended":1}),
                "photo_comments":API.photos.getAllComments({"owner_id":f_user.id, "need_likes":1, "count":100}),
                "videos":API.video.get({"owner_id":f_user.id, "count":200, "extended":1}),
                "wall":API.wall.get({"owner_id":f_user.id, "count":100}),
                "notes":API.notes.get({"user_id":f_user.id, "count":100}),
                "groups":API.groups.get({"user_id":f_user.id, "count":1000})
                };
        :param user_id:
        :return:
        """
        user_data = self.get('execute.userData', **{'user_id': user_id})
        user = VK_APIUser(user_data['user'])
        content_result = ContentResultIntelligentRelations(user.sn_id)
        # связи пользователя
        content_result.add_relations([(el, 'follower', user.sn_id) for el in user_data['followers']['items']])
        content_result.add_relations([(user.sn_id, 'friend', el) for el in user_data['friends']['items']])

        def fill_count(count_name):
            counter = user_data.get(count_name)
            if counter and len(counter):
                if isinstance(counter, dict):
                    user['%s_count' % count_name] = counter['count']
                    return counter['items']
                else:
                    user['%s_count' % count_name] = counter[0]
                    return counter[1:]
            return []

        # его подписки (то что он читает)
        content_result+=subscriptions_retrieve(fill_count('subscriptions'),user)
        # его фотографии и комментарии к ним
        content_result += photo_retrieve(fill_count('photos'))
        content_result += photo_comments_retrieve(fill_count('photo_comments'))
        # его видеозаписи
        content_result += video_retrieve(fill_count('videos'))
        # его стена
        content_result += wall_retrieve(fill_count('wall'))
        # его записки
        content_result += note_retrieve(fill_count('notes'))
        # его групы
        group_content_result = group_retrieve(fill_count('groups'), user)
        content_result+=group_content_result

        # укажем когда мы загрузили данные
        user['data_load_at'] = datetime.now()

        return user, content_result


if __name__ == '__main__':
    vk = VK_API_Execute()
    user, content_result = vk.get_user_data('from_to_where')
    print user
    print content_result

