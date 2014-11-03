
# coding=utf-8
import sys

from contrib.api.ttr import get_api
from contrib.core.characteristics import TTR_Characterisitcs
from contrib.core.social_net_graph import TTR_Graph
from contrib.db.database_engine import Persistent
from networkx import NetworkXNoPath
import properties

__author__ = '4ikist'

alpha = 2
beta = 2
log = properties.logger.getChild('latane_functions')


class LataneFunctions(object):
    def __init__(self, characteristics, social_net_graph):
        self.characteristics = characteristics
        self.social_net_graph = social_net_graph

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

        log.info('evaluate latane function for user: %s' % user)
        #возьмем всех пользователей которых искомый пользователь когда-либо упоминал
        mention_users = self.characteristics.mentions(user)
        x = 0
        log.info('mentioned users: \n%s' % '\n'.join(['%s\t:\t%s' % (k.get('screen_name'), v) for k, v in mention_users.iteritems()]))
        #будем перебирать пользователей упоминаемых
        for u_i in mention_users.keys():
            for u_j in mention_users.keys():
                if u_i == u_j:
                    continue
                #выберим
                val = max(mention_users.get(u_i), mention_users.get(u_j))
                log.info("evaluate shortest path between %s and %s" % (u_i.screen_name, u_j.screen_name))
                distance_from = self.social_net_graph.shortest_path_length(u_i, u_j)
                log.info("evaluate reverse shortest path")
                distance_to = self.social_net_graph.shortest_path_length(u_j, u_i)
                distance = max(distance_to, distance_from)
                distance = distance if distance != -1 else sys.maxint
                x += float(val) / pow(distance, alpha)

        result = -beta * sum(mention_users.values()) - x \
                 - evaluate_additional_force(self.characteristics.hashtags) if include_hash_tags else 0 \
                                                                                                      - evaluate_additional_force(
            self.characteristics.urls) if include_urls else 0

        return result


if __name__ == '__main__':
    api = get_api()
    persistent = Persistent()
    characteristics = TTR_Characterisitcs(persistent, api)
    social_net_graph = TTR_Graph(persistent, api)
    latane = LataneFunctions(characteristics, social_net_graph)

    # medved = persistent.get_user(screen_name='@medvedevRussia')
    result = latane.execute('@medvedevRussia')
    print result

        