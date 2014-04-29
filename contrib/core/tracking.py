# coding=utf-8
__author__ = '4ikist'

find_states = ['find_before_crossing', 'find_after_crossing']


class TTR_Tracking(object):
    def __init__(self, api, db):
        self.api = api
        self.db = db

    def get_relations_diff(self, user, delta, relations_type='friends'):
        saved_relations = self.db.retrieve_relations_for_diff(user.get('_id'), relation_type=relations_type)
        new = []
        remove = []
        acc = []
        from_cursor = -1
        cross_left = None
        updated_delta = delta
        while (updated_delta != 0):
            result = self.api.get_relation_ids(user, relations_type, from_cursor)
            updated_delta = delta
            if result:
                batch, cursor = result
                for i, batch_el in enumerate(batch):
                    if batch_el not in saved_relations:
                        new.append(batch_el)
                    else:
                        cross_right = saved_relations.index(batch_el)
                        if cross_left is None:
                            remove.extend(saved_relations[:cross_right])
                        else:
                            remove.extend(saved_relations[cross_left + 1:cross_right])
                        cross_left = cross_right
                    acc.append(batch_el)
                updated_delta -= len(new)
                updated_delta += len(remove)
                from_cursor = cursor
            else:
                break

        acc.extend(saved_relations[cross_left + 1:])
        self.db.save_relations_for_diff(user.get('_id'), acc, relations_type, new, remove)
        return new, remove, acc


if __name__ == '__main__':

    class FakeDB(object):
        def retrieve_relations_for_diff(self, user, relation_type):
            return [4, 5, 6, 10, 11, 13, 14, 15, 17, 18, 19, 20, 25, 26, 27, 28]

        def save_relations_for_diff(self, from_, relations, relation_type):
            for el in relations:
                print el

    class FakeApi(object):
        def __init__(self):
            self.count = 0

        def get_relation_ids(self, user, relation_type, cursor):
            if cursor == -1:
                return [1, 2, 3, 4], 1
            if cursor == 1:
                return [9, 11, 12, 13, 14, 15], 2
            if cursor == 2:
                return [17, 18, 19, 21, 22, 23, 24], 3
            if cursor == 3:
                return [25, 26, 27, 28, 29, 30], 4

        def get_user(self, screen_name):
            return {'friends_count': 10}

    tr = TTR_Tracking(FakeApi(), FakeDB())
    result = tr.get_relations_diff({'_id': None, 'friends_count': 5}, 10)
    print result[0], result[1]



