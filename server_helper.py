from datetime import datetime
from bson import DBRef

from contrib.db.database_engine import Persistent
from contrib.queue import QueueServer


__author__ = '4ikist'

db = Persistent()
queue = QueueServer()


def get_date(str, sn_name):
    if sn_name == 'ttr':
        #"Thu Nov 22 13:18:17 +0000 2012"
        return datetime.strptime(str, '%a %b %d %H:%M:%S +0000 %Y')
    if sn_name == 'fb':
        #2013-11-14T21:10:30+0000
        return datetime.strptime(str, '%Y-%m-%dT%H:%M:%S+0000')


def process_ttr_search_result(ttr):
    count_messages, count_users = 0, 0
    for el in ttr:
        user = el.get('user')
        user_ref = None
        if user:
            retrieved_user = {'name': user.get('name'),
                              'friends_count': user.get('friends_count'),
                              'followers_count': user.get('followers_count'),
                              'verified': user.get('verified') == 'true',
                              'sn_id': user.get('id'),
                              'sn_name': 'ttr',
                              'registered': get_date(user.get('created_at'), 'ttr'),
                              "location": user.get('location'),
                              "lang": user.get('lang'),
                              'screen_name': user.get('screen_name'),
                              'posts_count': user.get('statuses_count'),
                              'utc_offset': user.get('utc_offset'),
            }
            user_ref = db.save_user(retrieved_user)
            count_users += 1

        db.save_message({'text': el.get('text'),
                         'sn_id': el.get('id'),
                         'sn_name': 'ttr',
                         'user_ref': user_ref,
                         'metadata': el.get('metadata'),
                         'favorite_count': el.get('favorite_count'),
                         'retweeted': el.get('retweeted') == 'true',
                         'entities': el.get('entities'),
                         'created_at': get_date(el.get('created_at'), 'ttr')})
        count_messages += 1
    return count_messages, count_users


def process_fb_search_result(fb_result):
    count_users = 0
    count_messages = 0
    users = fb_result.get('user')
    for user in users:
        db.save_user({'sn_id': user.get('id'), 'name': user.get('name'), 'sn_name': 'fb'})
        count_users += 1

    posts = fb_result.get('post')
    for post in posts:
        db.save_message({'text': post.get('message'),
                         'title': post.get('name'),
                         'created_at': get_date(post.get('created_time'), 'fb'),
                         'sn_id': post.get('id'),
                         'sn_name': 'fb'})
        count_messages += 1

    for fb_social_object in ['proup', 'page', 'event']:
        search_result = fb_result.get(fb_social_object)
        for sr_object in search_result:
            corr_id = queue.send_message({'method': 'user_group_info', 'sn': 'fb',
                                          'params': {'group_id': sr_object.get('id'),
                                                     'group_type': fb_social_object}},
                                         priority=10)
            object_data = queue.wait_response(corr_id)
            if not object_data:
                continue

            social_object = {'sn_id': object_data['object'].pop('id'), 'sn_name': 'fb', 'type': fb_social_object}
            social_object.update(object_data['object'])
            object_id = db.save_social_object(social_object)
            object_ref = DBRef(db.social_objects.name, object_id)

            for relation_id, relation_data in object_data['posting_relations']:
                user_id = db.save_user({'sn_id': relation_id, 'sn_name': 'fb'})
                count_users += 1
                user_ref = DBRef(db.users.name, user_id)

                comments = relation_data.get('comments')
                if comments:
                    for comment in comments:
                        db.save_message({'sn_name': 'fb', 'text': comment, 'user_ref': user_ref})
                        count_messages += 1

                db.save_relation(user_ref, object_ref, {'type': 'like', 'count': relation_data['likes']})

            for rel_id, rel_data in object_data['relations']:
                user = {'sn_id': rel_id, 'sn_name': 'fb'}
                # user.update(rel_data)
                user_id = db.save_user(user)
                count_users += 1
                user_ref = DBRef(db.users.name, user_id)
                if fb_social_object == 'group':
                    for relation in rel_data['relations']:
                        db.save_relation(user_ref, object_ref, relation)


def process_search_result(result):
    """
    saving to database result of search.
    """
    count_users = 0
    count_messages = 0
    ttr = result.get('ttr')
    if ttr:
        count_messages_, count_users_ = process_ttr_search_result(ttr)
        count_messages += count_messages_
        count_users += count_users_

    fb = result.get('fb')
    if fb:
        count_messages_, count_users_ = process_fb_search_result(fb)
        count_messages += count_messages_
        count_users += count_users_


if __name__ == '__main__':
    print get_date("Thu Nov 22 13:18:17 +0000 2012", 'ttr')