# coding: utf-8
import datetime
import sys
from time import sleep
from contrib.api.ttr import get_api
from contrib.db.database_engine import Persistent
from properties import logger, update_iteration_time

__doc__ = """
Скрипт для слежения за пользователями, сохраняет в БД следующее:
sn_id пользователя
datetime когда было выкаченно
имя поля - значение на эту дату

время обновления задается в properties update_iteration_time

"""
__author__ = '4ikist'

ttr = get_api('ttr')
persist = Persistent()


log = logger.getChild('walker_ttr')

batch_count = 1000

def get_observed_users_ids(update_iteration_time):
    actual_date = datetime.datetime.now() - datetime.timedelta(seconds=update_iteration_time)
    result = {}
    for user_data in persist.get_users_iter({'update_date': {'$lte': actual_date}, 'source':'ttr'}):
        result[user_data.sn_id] = user_data
        if len(result) == batch_count:
            yield result
            result = {}
    yield result

def _is_changed_counts(do, dn):
    for k, v in do.iteritems():
        if u'count' in k and do[k] != dn[k]:
            return True
    return False

def get_user_changes(user_data, fresh_user_data):
    result = {}
    for k, v in fresh_user_data.iteritems():
        if k == 'status':
            # посморим на изменения текста статуса и его количества
            if user_data.get(k, None) is None or (v['text'] != user_data[k]['text'] or _is_changed_counts(user_data[k], v)):
                result[k] = v
        elif user_data.get(k) != v:
            result[k] = v

    return result


if __name__ == '__main__':
    if len(sys.argv) == 2:
        update_iteration_time = int(sys.argv[1])
    else:
        from properties import update_iteration_time

    while 1:
        for user_data_batch in get_observed_users_ids(update_iteration_time):
            users_datas,_ = ttr.get_users(user_data_batch.keys())
            for new_user_data in users_datas:
                old_user_data = user_data_batch.pop(new_user_data.sn_id)
                changes = get_user_changes(new_user_data, old_user_data)
                if len(changes):
                    # log.info('found changes (%s) for user: %s' %(len(changes), new_user_data.screen_name))
                    changes['sn_id'] = new_user_data.sn_id
                    changes['datetime'] = datetime.datetime.now()
                    persist.save_user_changes(changes)
                    persist.update_user_date(new_user_data.sn_id)

            if len(user_data_batch):
                log.info("users was deleted or some errors:\n%s"%'\n'.join([str(el) for el in  user_data_batch.keys()]))
                for k,v in user_data_batch.iteritems():
                    persist.add_deleted_user(k)
        sleep(3600)