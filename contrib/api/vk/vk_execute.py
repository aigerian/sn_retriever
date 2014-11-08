# coding=utf-8
from datetime import datetime
from contrib.api.entities import APIUser

from contrib.api.vk.utils import photo_retrieve, photo_comments_retrieve, video_retrieve, wall_retrieve, note_retrieve, \
    group_retrieve, subscriptions_retrieve, comments_retrieve, board_retrieve
from contrib.api.vk.vk import VK_API
from contrib.api.vk.vk_entities import ContentResult, get_mentioned, VK_APIUser, to_unix_time, VK_APISocialObject


__author__ = '4ikist'


def fill_count(user_data, user, count_name):
    counter = user_data.get(count_name)
    if counter and len(counter):
        if isinstance(counter, dict):
            user['%s_count' % count_name] = counter['count']
            return counter['items']
        else:
            user['%s_count' % count_name] = counter[0]
            return counter[1:]
    return []


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
                self.add_relations([(added_comment['owner']['sn_id'], 'mentions', el)
                                    for el in get_mentioned(added_comment['text'])])
            self.add_relations((added_comment['owner']['sn_id'], 'comment', self.user_id))

    def add_content(self, content_objects):
        count_added = super(ContentResultIntelligentRelations, self).add_content(content_objects)
        for added_content in self.content[-count_added:]:
            if added_content.get('owner') and added_content.get('text'):
                self.add_relations([(added_content['owner']['sn_id'], 'mentions', el)
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
            self.add_group(other.groups)
            return self
        raise ValueError('other is not my classg')


class VK_API_Execute(VK_API):
    def __init__(self, logins=None):
        super(VK_API_Execute, self).__init__(logins=logins)
        self.names = {'photos': self.get_photos_data,
                      'videos': self.get_videos_data,
                      'photo_comments': self.get_photos_comments_data,
                      'notes': self.get_notes_data,
                      'wall': self.get_wall_data}

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

    def get_group_data(self, group_id):
        """
        var f_user = API.groups.getById({"group_id":Args.group_id, "fields":"counters"})[0];
    return {
                "group":f_user,
                "photos":API.photos.getAll({"owner_id":-f_user.id, "count":200, "photo_sizes":1,"extended":1}),
                "photo_comments":API.photos.getAllComments({"owner_id":-f_user.id, "need_likes":1, "count":100}),
                "videos":API.video.get({"owner_id":-f_user.id, "count":200, "extended":1}),
                "wall":API.wall.get({"owner_id":-f_user.id, "count":100}),
                "boards":API.board.getTopics({"group_id":f_user.id, "count":1})
                };

        :param group_id:
        :return:
        """
        group_data = self.get('execute.groupData', **{'group_id': abs(group_id)})
        group = VK_APISocialObject(group_data['group'])
        content_result = ContentResult()
        content_result += board_retrieve(group_data['boards'], group.sn_id)
        content_result += video_retrieve(group_data['photo_comments'])
        content_result += photo_retrieve(group_data['photos'])
        content_result += wall_retrieve(group_data['wall'])
        return group, content_result

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
        content_result.add_relations([(el, 'follower', user.sn_id) for el in fill_count(user_data, user, 'followers')])
        content_result.add_relations([(user.sn_id, 'friend', el) for el in fill_count(user_data, user, 'friends')])

        # его подписки (то что он читает)
        subscription_result = subscriptions_retrieve(fill_count(user_data, user, 'subscriptions'), user.sn_id)
        # его фотографии и комментарии к ним
        photo_result = photo_retrieve(fill_count(user_data, user, 'photos'))
        photo_comment_result = photo_comments_retrieve(fill_count(user_data, user, 'photo_comments'), user.sn_id)
        # его видеозаписи
        video_result = video_retrieve(fill_count(user_data, user, 'videos'))
        # его стена
        wall_result = wall_retrieve(fill_count(user_data, user, 'wall'))
        # его записки
        note_result = note_retrieve(fill_count(user_data, user, 'notes'))
        # его групы
        group_content_result = group_retrieve(fill_count(user_data, user, 'groups'), user.sn_id)
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
        content_result += photo_comments_retrieve(comments_acc, user_id)
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

    def get_notes_data(self, user_id, since_date=None):
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
         var response = API.notes.get({"user_id":user_id, "count":100, "offset":offset});
         req_count = req_count - 1;
         comments = comments + response.items;
         offset = offset + 100;
         if (response.count < offset){
             return {"notes":comments};
         }
         if (req_count < 1){
             return {"notes":comments, "last_offset":offset, "all_count":response.count};
         }
        }

        :param user_id:
        :param since_date:
        :return:
        """
        notes_result = self.get("execute.get_notes", **{'user_id': user_id})
        notes_acc = self.__get_since(notes_result['notes'], since_date)
        if notes_result.get('offset'):
            notes_result = self.get("execute.get_notes",
                                    **{'user_id': user_id, 'offset': notes_result.get('offset')})
            notes_acc.extend(self.__get_since(notes_result['notes'], since_date))
        content_result = ContentResultIntelligentRelations(user_id)
        content_result += note_retrieve(notes_acc)
        return content_result

    def get_comments_data(self, user_id, object_type, object_id, since_date=None):
        """
        all scripts with postfix '_comments' exclude photo_comments
        :param user_id: user sn_id (int)
        :param object_type: must be [wall, video, note]
        :param object_id: not sn_id it must be identity deviate in user (post_id, video_id, note_id)
        :return:
        """
        result = self.get('execute.get_%s_comments' % object_type, **{'user_id': user_id, 'entity_id': object_id})
        result_acc = self.__get_since(result['comments'], since_date)
        if result.get('offset'):
            result = self.get('execute.get_%s_comments' % object_type,
                              **{'user_id': user_id, 'entity_id': object_id, "offset": result.get('offset')})
            result_acc.extend(self.__get_since(result['comments'], since_date))
        return comments_retrieve(result_acc, user_id, object_type, object_id)

    def get_likers(self, user_id, object_id, object_type):
        result = self.get('execute.get_likers',
                          **{'user_id': user_id, 'entity_id': object_id, 'entity_type': object_type})
        result_acc = result['likers']
        if result.get('offset'):
            result = self.get('execute.get_likers',
                              **{'user_id': user_id, 'entity_id': object_id, 'entity_type': object_type,
                                 "offset": result.get('offset')})
            result_acc.extend(result['likers'])
        content_result = ContentResult()
        content_result.add_relations([(el, 'likes', user_id) for el in result_acc])
        return content_result


    def get_wall_data(self, user_id, since_date=None):
        """
        this vk script
        var user_id = parseInt(Args.user_id);
        var req_count = 25;
        var comments = [];
        var offset = 0;
        if (Args.offset){
         offset = parseInt(Args.offset);
        }
        while (1){
         var response = API.wall.get({"owner_id":user_id, "count":100, "offset":offset, "extended":1,"filter":"all"});
         req_count = req_count - 1;
         comments = comments + response.items;
         offset = offset + 100;
         if (response.count < offset){
             return {"wall":comments};
         }
         if (req_count < 1){
             return {"wall":comments, "last_offset":offset, "all_count":response.count};
         }
        }
        :param user_id:
        :param since_date:
        :return:
        """
        wall_result = self.get("execute.get_wall", **{'user_id': user_id})
        wall_acc = self.__get_since(wall_result['wall'], since_date)
        if wall_result.get('offset'):
            wall_result = self.get("execute.get_wall",
                                   **{'user_id': user_id, 'offset': wall_result.get('offset')})
            wall_acc.extend(self.__get_since(wall_result['wall'], since_date))
        content_result = ContentResultIntelligentRelations(user_id)
        content_result += wall_retrieve(wall_acc)
        return content_result


if __name__ == '__main__':
    vk = VK_API_Execute()
    vk.get_group_data(26953)