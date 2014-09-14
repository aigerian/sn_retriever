# coding=utf-8
from datetime import datetime

from contrib.api.vk.utils import photo_retrieve, photo_comments_retrieve, video_retrieve, wall_retrieve, note_retrieve, \
    group_retrieve, subscriptions_retrieve
from contrib.api.vk.vk import VK_API
from contrib.api.vk.vk_entities import ContentResult, get_mentioned, VK_APIUser


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
                "photos":API.photos.getAll({"owner_id":f_user.id, "count":1000, "photo_sizes":1,"extended":1}),
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
        subscription_result = subscriptions_retrieve(fill_count('subscriptions'), user)
        # его фотографии и комментарии к ним
        photo_result = photo_retrieve(fill_count('photos'))
        photo_comment_result = photo_comments_retrieve(fill_count('photo_comments'))
        # его видеозаписи
        video_result = video_retrieve(fill_count('videos'))
        # его стена
        wall_result = wall_retrieve(fill_count('wall'))
        # его записки
        note_result = note_retrieve(fill_count('notes'))
        # его групы
        group_content_result = group_retrieve(fill_count('groups'), user)
        content_result += group_content_result + subscription_result + photo_comment_result + photo_result + video_result + wall_result + note_result

        # укажем когда мы загрузили данные
        user['data_load_at'] = datetime.now()

        return user, content_result

    def get_photos_data(self, user_id):
        """
        here is vk script:

var user_identity = Args.user_id;
var user_id = API.users.get({"user_ids":user_identity})[0].id;
var next_albums = Args.next_album_ids;
var last_offset = Args.last_offset;
var album_ids = null;
if (next_albums){
    album_ids = API.photos.getAlbums({"owner_id":user_id, "album_ids":next_albums}).items@.id;
}else{
    album_ids = API.photos.getAlbums({"owner_id":user_id, "need_system":1}).items@.id;
}
var album_counter = album_ids.length-1;
var req_counter = 23;
var photos = [];
var album_batch = [];
var offset = 0;
if (last_offset){
    offset = parseInt(last_offset);
}
var photos_at_album = offset+1;
while (1){
    while (photos_at_album - offset > 0){
        var photos_object = API.photos.get({"owner_id":user_id, "album_id":album_ids[album_counter], "count":1000, "offset":offset, "extended":1});
        req_counter = req_counter - 1;
        album_batch.push(photos_object.items);
        if (req_counter < 0){
            photos.push(album_batch);
            return {"photos":photos, "album_ids":album_ids, "next":album_ids.slice(0,album_counter),"last_offset":offset};
        }
        photos_at_album = photos_object.count;
        offset = offset + 1000;
    }
    photos.push(album_batch);
    album_batch = [];
    photos_at_album = 1;
    offset = 0;
    album_counter = album_counter-1;
    if (album_counter < 0){
        return {"photos":photos, "album_ids":album_ids,"next":null, "last_offset":null};
    }
}


        :param user_id: must be user sn_id not screen_name
        :return: all photos from all albums
        """
        def form_photos_acc(photo_acc):
            acc = []
            for album_els in photo_acc:
                for el in album_els:
                    if isinstance(el, list):
                        acc.extend(el)
                    else:
                        acc.append(el)
            return acc

        photos_data = self.get('execute.get_photos', **{'usr_id': user_id})
        photos_acc = photos_data['photos']
        while photos_data['next'] or photos_data['last_offset']:
            photos_data = self.get('get_photos', **{'usr_id': user_id, 'next_album_ids': photos_data['next'],
                                                    'last_offset': photos_data['last_offset']})
            photos_acc.extend(photos_data['photos'])

        result = form_photos_acc(photos_acc)
        return result


if __name__ == '__main__':
    # cr = ContentResult()
    # cri = ContentResultIntelligentRelations(1)
    # print isinstance(cri,cr.__class__)
    vk = VK_API_Execute()
    vk.get_photos_data(114924709)

