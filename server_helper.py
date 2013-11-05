from datetime import datetime
from time import gmtime
from bson import DBRef

from contrib.db_connector import db_handler


__author__ = '4ikist'

db = db_handler()


def get_date(str, sn_name):
    if sn_name == 'ttr':
        #"Thu Nov 22 13:18:17 +0000 2012"
        return datetime.strptime(str, '%a %b %d %H:%M:%S +0000 %Y')


def process_search_result(result):
    """
    saving to database result of search.

    """
    ttr = result.get('ttr')
    if ttr:
        for el in ttr:
            user = el.get('user')
            user_ref = None
            if user:
                name = user.get('name')
                friends_count = user.get('friends_count')
                followers_count = user.get('followers_count')
                verified = user.get('verified') == 'true'
                sn_id = user.get('id')
                sn_name = 'ttr'
                registered = get_date(user.get('created_at'), 'ttr')
                retrieved_user = {'name': name,
                                  'friends_count': friends_count,
                                  'followers_count': followers_count,
                                  'verified': verified,
                                  'sn_id': sn_id,
                                  'sn_name': sn_name,
                                  'registered': registered
                }
                retrieved_user.update({
                    "location": user.get('location'),
                    "lang": user.get('lang'),
                    'screen_name': user.get('screen_name'),
                    'posts_count': user.get('statuses_count'),
                    'utc_offset': user.get('utc_offset'),
                })
                user_id = db.users.save(retrieved_user)
                user_ref = DBRef(db.users.name, user_id)

            db.messages.save({'text': el.get('text'),
                              'sn_id': el.get('id'),
                              'sn_name': 'ttr',
                              'user_ref': user_ref,
                              'metadata': el.get('metadata'),
                              'favorite_count': el.get('favorite_count'),
                              'retweeted': el.get('retweeted') == 'true',
                              'entities': el.get('entities'),
                              'created_at': get_date(el.get('created_at'), 'ttr')})



if __name__ == '__main__':
    print get_date("Thu Nov 22 13:18:17 +0000 2012", 'ttr')