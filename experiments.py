from contrib.api.ttr import __TTR_API

__author__ = '4ikist'

api = __TTR_API()
right_users = []
right_users.append(api.get_user('@medvedevRussia'))
right_users.append(api.get_user('@PutinRF'))
right_users.append(api.get_user('@KremlinRussia'))
right_users.append(api.get_user('@Pravitelstvo_RF'))

left_users = []
left_users.append(api.get_user('@navalny'))
left_users.append(api.get_user('@tvrain'))
left_users.append(api.get_user('@EchoMskRu'))

def get_followers(user_list):
    for user in user_list:
        followers = api.get_relations(user_id=user.id, relation_type='followers')
        friends = api.get_relations(user_id=user.id, relation_type='friends')

