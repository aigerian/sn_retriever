# coding=utf-8
from contrib.api.ttr import TTR_API
from contrib.core.characteristics import TTR_Characterisitcs
from contrib.db.database_engine import Persistent, GraphPersistent

__author__ = '4ikist'

alpha = 2
beta = 2


class LataneFunctions(object):
    def __init__(self, characteristics, graph_persistence):
        self.characteristics = characteristics
        self.graph_persistence = graph_persistence

    def execute(self, user, include_hash_tags=False, include_urls=False):
        """
        Возвращает количество социального давления направленного на индивидуума
        """

        def evaluate_additional_force(force_function):
            result = 0
            elements = force_function(user)
            for u_i in elements.keys():
                for u_j in elements.keys():
                    if u_i == u_j:
                        continue
                    val = max(elements.get(u_i), elements.get(u_j))
                    result += val
            return result

        #возьмем всех пользователей которых искомый пользователь когда-либо упоминал
        mention_users = self.characteristics.mentions(user)
        x = 0
        #будем перебирать пользователей упоминаемых
        for u_i in mention_users.keys():
            for u_j in mention_users.keys():
                if u_i == u_j:
                    continue
                #выберим
                val = max(mention_users.get(u_i), mention_users.get(u_j))
                distance_friends = self.graph_persistence.get_path_length(u_i, u_j, 'friends', False)
                distance_followers = self.graph_persistence.get_path_length(u_i, u_j, 'followers', False)
                distance = max(distance_friends, distance_followers)
                x += float(val) / pow(distance if distance is not None else 1, alpha)

        result = -beta * sum(mention_users.values()) - x \
                 - evaluate_additional_force(self.characteristics.hashtags) if include_hash_tags else 0 \
                                                                                                      - evaluate_additional_force(
            self.characteristics.urls) if include_urls else 0

        return result


if __name__ == '__main__':
    characteristics = TTR_Characterisitcs(Persistent(), TTR_API())
    graph_persistence = GraphPersistent()
    latane = LataneFunctions(characteristics,graph_persistence)

        