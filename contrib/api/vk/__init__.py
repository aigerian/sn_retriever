# coding=utf-8
from datetime import datetime
import random
import string

from contrib.api.entities import APISocialObject, APIUser, APIContentObject, APIMessage
from contrib.api.vk.vk_entities import rel_types_groups, ContentResult, rel_types_users
from contrib.api.vk.vk_execute import VK_API_Execute
import properties

__author__ = '4ikist'

log = properties.logger.getChild('vk')

rand_str = lambda cnt: ''.join([str(random.choice(string.ascii_letters)) for el in xrange(cnt)])


class FakeVK(VK_API_Execute):
    def get_groups_info(self, group_ids):
        return [APISocialObject({'sn_id': random.randint(0, 1000)}) for el in xrange(10)]

    def get_user_info(self, user_id):
        return [APIUser({'sn_id': random.randint(0, 1000000), 'screen_name': rand_str(el * 3)}) for el in xrange(10)]


class FakeContentResult(ContentResult):
    def __init__(self):
        super(FakeContentResult, self).__init__()
        self.add_comments(
            [APIMessage({'sn_id': el * random.randint(0, 3917333),
                         'user': APIUser({'sn_id': random.randint(0, 1000000),
                                          'screen_name': rand_str(el * 3)})}) for el in
             xrange(random.randint(0, 1000))])
        self.add_content(
            [APIContentObject({'sn_id': el * random.randint(0, 3917333),
                               'user': APIUser({'sn_id': random.randint(0, 1000000),
                                                'screen_name': rand_str(el * 3)})}) for el in
             xrange(random.randint(0, 100))])
        for el in rel_types_groups:
            self.add_relations((random.randint(0, 1000), el, random.randint(0, 1000)))
        for el in rel_types_users:
            self.add_relations((random.randint(0, 1000), el, random.randint(0, 1000)))


def persist_content_result(content_result, user_id, persist, vk):
    """
    Сохраняет результат правильно. Сначала пользователей и их связи, а потом их данные. Ибо чтобы было привязывать к кому.
    Пользователей загружает скопом
    :param content_result: контент который сохраняем
    :param user_id: идентификатор пользователя которого сохраняем
    :return:
    """
    if content_result is None:
        return

    not_data_loaded_users = []
    not_loaded_users = []
    not_loaded_groups = []

    def add_new_user(new_user_id):
        if new_user_id != user_id:
            is_loaded = persist.is_user_data_loaded(new_user_id)
            if isinstance(is_loaded, datetime):
                return
            elif is_loaded == True:
                not_data_loaded_users.append(new_user_id)
            else:
                not_loaded_users.append(new_user_id)

    def add_new_group(group_id):
        if not persist.is_social_object_saved(group_id):
            not_loaded_groups.append(group_id)

    for from_id, types_and_tos in content_result.get_relations().iteritems():
        for rel_type, tos in types_and_tos.iteritems():
            for to in tos:
                if rel_type not in rel_types_groups:  # если связь не с группой
                    add_new_user(from_id), add_new_user(to)
                elif rel_type in rel_types_groups:
                    add_new_group(to)
            persist.save_relation(from_id, tos, rel_type)
    log.info("found %s related and not loaded users" % len(not_loaded_users))
    log.info("found %s related and not data loaded users" % len(not_data_loaded_users))
    log.info("found %s related and not loaded groups" % len(not_loaded_groups))
    log.info("will load....")
    groups = vk.get_groups_info(not_loaded_groups)
    persist.save_object_batch(groups)

    users = vk.get_users_info(not_loaded_users)
    log.info('load %s users info' % len(users))
    persist.save_object_batch(users)

    persist.save_object_batch(content_result.get_content_to_persist())
    return not_data_loaded_users + not_loaded_users
