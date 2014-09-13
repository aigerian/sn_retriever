# coding=utf-8
from contrib.api.vk.vk_execute import social_objects_relations_type

__author__ = '4ikist'

def persist_content_result(content_result, user_id, persist):
    """
    Сохраняет результат правильно. Сначала пользователей и их связи, а потом их данные.
    Пользователей загружает скопом
    :param content_result:
    :return:
    """
    output_users = []
    not_loaded_users = []

    def add_new_user(new_user_id):
        if new_user_id != user_id:
            if not persist.is_loaded(new_user_id):
                not_loaded_users.append(new_user_id)
                output_users.append(new_user_id)

    for from_id, rel_type, to_id in content_result.relations:
        if rel_type not in social_objects_relations_type: #если связь не с группой
            add_new_user(from_id), add_new_user(to_id)
        persist.save_relation(from_id, rel_type, to_id)

    users = vk.get_users_info(not_loaded_users)
    persist.save_object_batch(users)

    persist.save_object_batch(content_result.get_content_to_persist())
    return output_users
