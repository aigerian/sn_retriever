from datetime import datetime
import sys
from contrib.api.vk.utils import persist_content_result

from contrib.api.vk.vk_execute import VK_API_Execute, iterated_counters
from contrib.db.database_engine import Persistent
from properties import logger

__author__ = '4ikist'

persist = Persistent()
vk = VK_API_Execute()
log = logger.getChild('walker_ttr')


def get_changes(old_user, new_user):
    changes = {'sn_id': old_user.sn_id, 'datetime': datetime.now()}
    for k, v in new_user.iteritems():
        old_value = old_user.get(k)
        if '_count' in k:
            delta = v - old_value
            if delta < 0:
                pass
            if  delta > iterated_counters.get(k[:len('_count')]):
                pass
                # TODO process this!

        if old_value != v:
            changes[k] = v

    return changes


if __name__ == '__main__':
    if len(sys.argv) == 2:
        update_iteration_time = int(sys.argv[1])
    else:
        from properties import update_iteration_time
    while 1:
        for user_batch in persist.get_observed_users_ids(update_iteration_time, 'vk'):
            for user_sn_id, saved_user in user_batch.iteritems():
                updated_user, content_result = vk.get_user_data(user_sn_id)
                changes = get_changes(saved_user, updated_user)
                if len(changes) > 2:
                    log.info("found change for user %s" % updated_user.sn_id)
                    persist.save_user_changes(changes)
                    persist_content_result(content_result, updated_user.sn_id, persist)