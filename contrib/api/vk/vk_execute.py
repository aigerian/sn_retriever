# coding=utf-8
from datetime import datetime

from contrib.api.vk.utils import photo_retrieve, photo_comments_retrieve, video_retrieve, wall_retrieve, note_retrieve, \
    group_retrieve, subscriptions_retrieve
from contrib.api.vk.vk import VK_API
from contrib.api.vk.vk_entities import ContentResult, get_mentioned, VK_APIUser, to_unix_time


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

    def e_i(self, other):
        """
        extend intelligent
        :param other:
        :return:
        """
        if isinstance(other, self.__class__) or isinstance(self, other.__class__):
            self.add_comments(other.comments)
            self.add_content(other.content)
            self.add_relations(other.relations)
            return self
        raise ValueError('other is not my classg')



class VK_API_Execute(VK_API):

    def __init__(self):
        super(VK_API_Execute, self).__init__()
        self.names = {'photo':self.get_photos_data, 'video':self.get_videos_data, 'photo_comments':self.get_photos_comments_data}

    def __get_since(self, new_batch, date):
        if date:
            result = []
            for el in iter(new_batch):
                if el['date'] > date:
                    result.append(el)
            return result
        return new_batch

    def execute_by_name(self, name, **kwargs):
        if name in self.names:
            return self.names[name](**kwargs)
        return None

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
        content_result.e_i(
            group_content_result + subscription_result + photo_comment_result + photo_result + video_result + wall_result + note_result)

        # укажем когда мы загрузили данные
        user['data_load_at'] = datetime.now()

        return user, content_result

    def get_photos_data(self, user_id, since_date=None):
        """
        here is vk script:

        var user_id = parseInt(Args.user_id);
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
                album_batch = album_batch + photos_object.items;
                if (req_counter < 0){
                    photos = photos+album_batch;
                    return {"photos":photos, "album_ids":album_ids, "next":album_ids.slice(0,album_counter),"last_offset":offset};
                }
                photos_at_album = photos_object.count;
                offset = offset + 1000;
            }
            photos = photos+album_batch;
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
        photos_data = self.get('execute.get_photos', **{'user_id': user_id})
        photos_acc = self.__get_since(photos_data['photos'], date=since_date)
        while photos_data.get('next') is not None or photos_data.get('last_offset') is not None:
            photos_data = self.get('execute.get_photos', **{'user_id': user_id,
                                                            'next_album_ids': photos_data['next'],
                                                            'last_offset': photos_data['last_offset']})
            photos_acc.extend(self.__get_since(photos_data['photos'], date=since_date))
        return photo_retrieve(photos_acc)


    def get_photos_comments_data(self, user_id, since_date=None):
        """
        here is vk script

        var user_id = parseInt(Args.user_id);
        var req_count = 25;
        var comments = [];
        var offset = 0;
        if (Args.offset){
         offset = parseInt(Args.offset);
        }
        while (1){
         var response = API.photos.getAllComments({"owner_id":user_id, "need_likes":1, "count":100,"offset":offset});
         req_count = req_count - 1;
         comments = comments + response.items;
         offset = offset + 100;
         if (response.count < offset){
             return {"comments":comments};
         }
         if (req_count < 1){
             return {"comments":comments, "last_offset":offset, "all_count":response.count};
         }
        }

        :param user_id:
        :return: all comments of all photos
        """
        comments_result = self.get("execute.get_photos_comments", **{'user_id': user_id})
        comments_acc = self.__get_since(comments_result['comments'], since_date)
        if comments_result.get('offset'):
            comments_result = self.get("execute.get_photos_comments",
                                       **{'user_id': user_id, 'offset': comments_result.get('offset')})
            comments_acc.extend(self.__get_since(comments_result['comments'], since_date))
        content_result = ContentResultIntelligentRelations(user_id)
        content_result += photo_comments_retrieve(comments_acc)
        return content_result

    def get_videos_data(self, user_id, since_date=None):
        """
        here vk_script code:
        var user_id = parseInt(Args.user_id);
        var req_count = 25;
        var comments = [];
        var offset = 0;
        if (Args.offset){
         offset = parseInt(Args.offset);
        }
        while (1){
         var response = API.video.get({"owner_id":user_id, "extended":1, "count":200, "offset":offset});
         req_count = req_count - 1;
         comments = comments + response.items;
         offset = offset + 200;
         if (response.count < offset){
             return {"videos":comments};
         }
         if (req_count < 1){
             return {"videos":comments, "last_offset":offset, "all_count":response.count};
         }
        }

        :param user_id:
        :return: all videos of user
        """
        videos_result = self.get("execute.get_videos", **{'user_id': user_id})
        videos_acc = self.__get_since(videos_result['videos'], since_date)
        if videos_result.get('offset'):
            videos_result = self.get("execute.get_videos",
                                     **{'user_id': user_id, 'offset': videos_result.get('offset')})
            videos_acc.extend(self.__get_since(videos_result['videos'], since_date))
        content_result = ContentResultIntelligentRelations(user_id)
        content_result += video_retrieve(videos_acc)
        return content_result


def test_asc(acc):
    for i, el in enumerate(acc):
        if i > 0 or i < len(acc) - 1:
            if not (acc[i - 1]['date'] >= el['date'] and el['date'] >= acc[i + 1]['date']):
                return (acc[i - 1], acc[i], acc[i + 1])


if __name__ == '__main__':
    # cr = ContentResult()
    # cri = ContentResultIntelligentRelations(1)
    # print isinstance(cri,cr.__class__)
    vk = VK_API_Execute()
    # user = vk.get_user_info('togeefly')
    # photos_result = vk.get_photos_data(user.sn_id)
    # last_photo = photos_result.content[4]
    # next_photo_result = vk.get_photos_data(user.sn_id, last_photo.sn_id)
    # photos = vk.get_photos_data(1022960)
    photo_comments = vk.get_photos_comments_data(1022960)
    # len(photo_comments.content)

