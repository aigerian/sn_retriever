# coding=utf-8
from datetime import datetime
import sys
from contrib.api.vk.utils import persist_content_result
from contrib.api.vk.vk_entities import rel_types_users

from contrib.api.vk.vk_execute import VK_API_Execute
from contrib.db.database_engine import Persistent
from properties import logger
import properties


__author__ = '4ikist'

persist = Persistent(truncate=False)

log = logger.getChild('walker_ttr')
vk = VK_API_Execute()


def persist_all_user_data_and_retrieve_related(user_id):
    saved_user = persist.get_user(sn_id=user_id)
    # Если пользователь уже сохранен и его данные сохранены недавно то возвращаем его пользовательские
    if saved_user and 'data_load_at' in saved_user and (
                datetime.now() - saved_user['data_load_at']).total_seconds() < properties.update_iteration_time:
        log.info('user %s was load but date of load data is so far' % saved_user.screen_name)
        related_users = [persist.get_related_users(saved_user.sn_id, relation_type=el, only_sn_ids=True) for el in
                         rel_types_users]
        return reduce(lambda x, y: x+y, related_users, [])

    user, result_object = vk.get_user_data(user_id)
    log.info("user [%s (%s)] data was retrieved, saving..." % (user.screen_name, user.name))
    persist.save_user(user)
    related_users = persist_content_result(result_object, user.sn_id, persist, vk)
    return related_users


if __name__ == '__main__':
    try:
        start_user_id = sys.argv[1]
    except:
        print "usage is:\nwalker_vk.py <start_user_id_or_screen_name>"
        print "now you forgot last parameter"
        sys.exit(0)
    log.info("Starting... Retrieving user info for user: %s" % start_user_id)
    related_users = persist_all_user_data_and_retrieve_related(start_user_id)
    while 1:
        new_related_users = []
        for user_id in related_users:
            log.info("Retrieving data for user %s" % user_id)
            new_related_users.extend(persist_all_user_data_and_retrieve_related(user_id))
        related_users = list(set(new_related_users))





