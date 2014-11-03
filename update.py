# coding=utf-8
from contrib.db.database_engine import Persistent

__author__ = '4ikist'

__doc__ = """Обновляет пользователей уже сохраненных и прописывыает всем у кого не задан source равным ttr """

persist = Persistent()
def update_data_for_source():
    counter = 0
    for user in persist.get_users_iter({'source':{'$exists':False}}):
        counter += 1
        user['source'] = 'ttr'
        persist.save_user(user)
    print "updated %s users" % counter
    counter = 0
    for message in persist.get_messages_iter({'source':{'$exists':False}}):
        counter+=1
        message['source'] = 'ttr'
        persist.save_message(message)
    print 'updated %s messages' %counter

def update_data_for_owner():
    counter = 0
    for message in persist.get_messages_iter({'user':{'$exists':True}}):
        counter+=1
        message['owner'] = message.pop('user')
        message['owner_id'] = message.pop('user_id', None)
        persist.save_message(message)
    print 'updated %s messages' %counter

    # for social_object in  persist.get_social_object({'user':})

if __name__ == '__main__':
    update_data_for_owner()
