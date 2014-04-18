__author__ = '4ikist'


class DataBase(object):
    def get_users(self):
        pass

    def get_user(self, user_id):
        pass

    def save_message(self, message):
        pass

    def save_user(self, user):
        """
        :param user: dict representation of user
        :return: id of user
        """
        pass

    def save_social_object(self, s_object):
        """
        :param s_object:
        :return:
        """
        pass

    def save_relation(self, from_, to_, relation_data=None):
        """
        :param from_:
        :param to_:
        :param relation_data:
        :return:
        """
        pass