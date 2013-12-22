__author__ = '4ikist'



class API(object):
    def __auth(self):
        pass

    def get(self, method_name, **kwargs):
        pass

    def get_relations(self, user_id, relation_type='friends'):
        pass

    def search(self, q):
        pass


class APIRequestOverflowException(Exception):
    pass


class APIException(Exception):
    pass