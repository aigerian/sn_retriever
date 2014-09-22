# coding=utf-8
from datetime import datetime
import sys
from contrib.api.vk import persist_content_result
from contrib.api.vk.vk_entities import rel_types_users

from contrib.api.vk.vk_execute import VK_API_Execute
from contrib.db.database_engine import Persistent
from properties import logger
import properties


__author__ = '4ikist'

persist = Persistent(truncate=__debug__)

log = logger.getChild('walker_ttr')
vk = VK_API_Execute()


def persist_all_user_data_and_retrieve_related(user_id):
    saved_user = persist.get_user(sn_id=user_id)
    # Если пользователь уже сохранен и его данные сохранены  то возвращаем его пользовательские связи которые не были сохранены
    related_users_with_not_loaded_data = []
    if saved_user:
        related_users_with_not_loaded_data = [el for el in
                                              persist.get_related_users(user_id, rel_types_users, only_sn_ids=True,
                                                                        backwards=True) if
                                              persist.is_user_data_loaded(el) == 'not_data_load']
        if saved_user.get('data_load_at'):
            return related_users_with_not_loaded_data

    user, result_object = vk.get_user_data(user_id)
    log.info("user [%s (%s)] {%s} data was retrieved, saving..." % (user.screen_name, user.name,user.sn_id))
    persist.save_user(user)
    related_users = persist_content_result(result_object, user.sn_id, persist, vk)
    return related_users + related_users_with_not_loaded_data


if __name__ == '__main__':
    try:
        start_user_id = sys.argv[1]
    except:
        print "usage is:\nwalker_vk.py <start_user_id_or_screen_name>"
        print "now you forgot last parameter"
        sys.exit(0)
    log.info("Starting... Retrieving user info for user: %s" % start_user_id)
    related_users = persist_all_user_data_and_retrieve_related(start_user_id)
    log.info("Started relations count: %s" % len(related_users))
    while 1:
        new_related_users = []
        for user_id in related_users:
            log.info("Retrieving data for user %s" % user_id)
            _new_related_users = persist_all_user_data_and_retrieve_related(user_id)
            log.info("for user %s found %s relations" % (user_id, len(_new_related_users)))
            new_related_users.extend(_new_related_users)

        related_users = list(set(new_related_users))
        if len(related_users) == 0:
            break





