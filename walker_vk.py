from contrib.api.vk import VK_API
from contrib.db.database_engine import Persistent
from properties import logger

__author__ = '4ikist'

relation_type = 'friends'
start_user_screen_name = 'linoleum2k12'


persist = Persistent()

log = logger.getChild('walker_ttr')
vk = VK_API()

def persist_all_user_data_and_retrieve_friends_ids(user_id):
    user = vk.get_user(user_id)
    persist.save_user(user)





