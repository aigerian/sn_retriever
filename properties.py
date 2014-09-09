# coding=utf-8
"""
file for properties
"""
import random

__author__ = '4ikist'

import logging
import sys
import os


def module_path():
    if hasattr(sys, "frozen"):
        return os.path.dirname(
            unicode(sys.executable, sys.getfilesystemencoding())
        )
    return os.path.dirname(unicode(__file__, sys.getfilesystemencoding()))


certs_path = os.path.join(module_path(), 'cacert.pem')

sleep_time_long = lambda: 60 * random.randint(2, 5)
sleep_time_short = lambda: random.randint(1, 4)
tryings_count = 5

# facebook application credentials
fb_app_id = '182482928555387'
fb_app_secret = 'd8188882ccf227f3b1c1b2f31b7f4429'
fb_client_token = '655cffd14ae5a391b89197e3e5dc3e12'

fb_user_email = 'alexey.proskuryakov@gmail.com'
fb_user_pass = 'sederfes_fb#'

# данные для твитера
#linoleum2k12 / aspiranture_ttr!
#sederfes / sederfes100500 / stack2008@gmail.com
#pramen2 / sederfes100500 / pramen.toramen@gmail.com
#kilogram_tabaka / sederfes100500 / sofia.bortnicova@gmail.com
#ariantis_mar / sederfes100500 / ariantis.marcerinz@gmail.com

ttr_consumer_keys = {1: 'VbDKb4QMLwe5YsdHESNFOg',
                     2: 'BNFvKYnVrvD4WldufjahMw',
                     3: 'BzUudc7uHds640tSzSJVg',
                     4: 'QBLLRpfESqEuvJ2Bnai8AA',
                     5: 'ZFIwiYyE0ZkzQ2qabQizA',
                     6: 'dcvDFZq9Z1HxzlG61iZpLA',
                     7: 'CiMKUgN6XzqjLgwEwt0liQ',
                     8: 'ds67b6pcQrqyNssSVC20gA',
                     9: 'g2EMHObh7F6Nxza66ipFQ',
                     10: 'srKpeQundvs8HuBP67qjTg',
                     11: 'HoB6XVlJsPkjnzeqf7UFSw',
                     12: '5ctEos2gep2RzLbuNlwymw',
                     13: 'CEnEMMj03A5sS4yq08DQ',
                     14: 'fGWHMaaw1JnaETr3jVYjw',
                     15: '796NPXiZT3sKi9z2rX8IQ',
                     16: 'CNtgbk3JHp7tVHw8RDV4XA',
                     17: 'TUicSSe8Waqv4ubMFAAqQ',

}

ttr_consumers_secret = {1: 'cEaSWdxHnQ6I3sGYaIBufjahyDsAP0SY5lx1YCI',
                        2: 'Rn2r8jABTuykaV3KJbGOUCAytIqVmoglwbHGAmdHj3Y',
                        3: '7NrhRuBekU7lMmzAX3lEa8mc0rQ0zzX5m4KVIbgqM',
                        4: 'ppurRIrJJXeNNGVIfkXmvgmpAodbHq9BbuVhUiVKQ',
                        5: 'pwRn5WmRP71ckv07qUz7cqT7OQacTajlcLnblqZsc',
                        6: 'MvurUBGKvi0OzpDNWGALyaFPiFlWFXOqjaysL3Hs1iA',
                        7: 'fJymWzYaIfYuxrzyVSy2Hb3I0dRj1B7BBFKAIOHq4Nk',
                        8: 'wfSFn8fuVIPsyYKYXK3lqKA8bpXW3L5MgePYWBXAnM',
                        9: 'HgbgNpoFC68DxxhdetSqnvkxxSGo3kKPnJPvOAHhvc',
                        10: 'hqq04ds1veJdB2INSa1lYSeYOjOIKDkvSfuVzCLGNig',
                        11: 'SEmFHC76FFOAUSTux7xlX8pkvpklWyTmqBbJDYeXf84',
                        12: 'icnlUiNCyDJKZXATPWqpJjtJ0Sofawa98mr7uzCTU',
                        13: '0Kx4OlK5XtID282TbTixtFrFFHmViCVVebmZqoS1w',
                        14: 'Fa39brPNhZmLtn8iuGqQdKAbSwqmTklmzJ8u0YV6pU',
                        15: 'Xhl2LLtVy4jMcwpmWxhdhI2ujlvS8gmCe83wYvVidqw',
                        16: 'KdjuZbcGmV5u3zcJjDiy6llVLFlny5PFqOPC1IUWg',
                        17: 'C4aXF9jPM1HALNHL7tnlzJnCLHo2UFl67KCPLNSQ',

}

ttr_access_tokens = {1: '612776846-80PPCl8bpLD6hcXSHudaMEUajBrLHHE8b9d31Tzk',
                     2: '612776846-LpqUhkru4ELYUBY0tbyLn9l33J9eC6MFW8fQux9r',
                     3: '612776846-d0OQqF3DPBz1lCZQSnVdsgjQOf0VYuvAJ0FCHaap',
                     4: '612776846-8ftQinWTF1qDbpA3RybWq2m3qnSjgyaaCzqcJPb7',
                     5: '612776846-mhnRxQ5nl7B096w4xThNMBufKDGIPwdBbNkTtLHl',
                     6: '2391549558-5gLTxjJXt15KeOB5qtxdQ1sPjQJBkG2jA7PMAm1',
                     7: '2391549558-2lTTIiX1cP3XIxCDi4321YLTVnLUCDslNNcGHyK',
                     8: '2391549558-ewfkQHlh6LEGasZP48yywLAvIydafe67EqVRMCe',
                     9: '2391566808-I3JFo5WBCXHtm3k58VEhMe2PwnPGGluarj5ghzd',
                     10: '2391566808-9cbPBxkcfHXflI4OZlvHSJjzSIsBs57C0Sv9CUf',
                     11: '2391566808-O69B1SeNPYxsqYa1GP0maO3Q3u3lV48y4o5Y7si',
                     12: '2393041968-kAd3ptKn25zXMqCBD0i1MNZl9P1Tbfxd7eXYD46',
                     13: '2393041968-kXl0HGzHFzxMWqAOqBOUVS9nmS1OjzPSVG8ljZp',
                     14: '2393041968-M9jp7UiEgDM1McYsA7XwV7F2D7GwEo8PBVYQouw',
                     15: '2393069306-6qDu3XmFzMhK1Fv1UzxlFcQwfVwh3oAShGlcg7w',
                     16: '2393069306-1omMMpftA7nOMOYGIq5txf6sxfPnN3CSKLDCB2r',
                     17: '2393069306-aBbb4n995vXWlldT2K6ZBdm46jh0ER22cBEvOAf',
}

ttr_access_tokens_secret = {1: 'H9dfxvLnxT9HGw7PH2NQsBAKbup1qEgz81UrURqAeCkaA',
                            2: 'rz8KE7B80ToQBsP3H8W14YEKqtI0y78xBHgpfhc2m65hn',
                            3: 'NFxRVZOAKsjFNhqIoZZ6TvAJhiphfYCO6XuDgzS4NzGJ1',
                            4: '6vuX0K9o07ane4czlX5hRBNTtrWlhF8XE3RCawhYUqXom',
                            5: 'K0yK7R1FrI6AFuWF33U8VlOqoCGJujHBhVD4IENZt7UKQ',
                            6: 'P0MxBuFAuVWxD4NvLqpgwyMYKjuOxmcwAYzSKxNw0o4V1',
                            7: 'dtHsLqOfiKjvsAZet6OeRWb5YiZ0ZIHkOeSu4Qmjg2EoL',
                            8: 'D35rBqA74GqZEFPXi3ulVrDNjKkGF36L5MUHuQpQzH1kl',
                            9: 'PMrhFJF48Q4f0PaQUTXrYOy10Smknv0gK2VQdYh7ezgPJ',
                            10: 'f0CEtWepURte2tLsV51wXIGNv6tDMKZ52gtJbIUSPBEZK',
                            11: 'O469Pp08VF5EUJb3iHbJv4YGXE6gu1ftKHLcHg4liiX4Q',
                            12: 'FrFUGzSpzQDwEzYCXGgvzxvX5u5facnei7Z5OJ61G7GTQ',
                            13: 'haxdh0KOsNU7tI4SvTqRX2S0tllUQuuljKWhzIIHu6PR2',
                            14: 'xQc6V53h4X7xPlg3BQ1DIWt7YTh1FfCkQSJXRcBxdJEjF',
                            15: 'U2fDtsmZ0wA1iVOVOn4Zx0mhcpnkbkgTLHDlfiLonheIH',
                            16: '6lx8y8AdYXxEuQQr8B8t4PudG1486vNKGLThBmPfRp5lh',
                            17: 'X547yZFFIjxeqabfo2fCjqB4pceSvNdFv4WkLz3UnjcJs'
}


def get_ttr_credentials(number):
    return {'consumer_key': ttr_consumer_keys[number],
            'consumer_secret': ttr_consumers_secret[number],
            'access_token': ttr_access_tokens[number],
            'access_token_secret': ttr_access_tokens_secret[number]}

#vk application credentials
vk_key = 'mRNxuLGPrSCtuqLl9DkU'
vk_app_name = 'vk_retr'

vk_logins = {#1: '+79811064022',
             # 2: '+79060739957',
              3: '+79138973664',
             # 4: '+79060740391',
             # 5: '+79516739528'
}

vk_pass = 'sederfes100500'

vk_user_fields = 'sex, bdate, city, country, photo_max_orig, domain, has_mobile, contacts, connections, site, education, universities, schools, can_see_all_posts, can_see_audio, can_write_private_message, status, last_seen, common_count, relation, relatives, counters, screen_name, maiden_name, timezone, occupation,activities, interests, music, movies, tv, books, games, about, quotes '
vk_group_fields = 'city, country, place, description, wiki_page, members_count, counters, start_date, end_date, activity'
#vk helper...
vk_access_credentials = {'client_id': '3784486',
                         # 'scope': 'notify,friends,photos,audio,video,docs,notes,pages,status,offers,questions,wall,groups,messages',
                         'scope': 999999,
                         'redirect_uri': 'https://oauth.vk.com/blank.html',
                         'display': 'mobile',
                         'v': 5.24,
                         'response_type': 'token',
                         }
#also...
vk_edit_app_url = 'https://vk.com/editapp?id=3784486&section=options'


#настройки логирования
log_file = os.path.join(module_path(), 'result.log')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
fh = logging.FileHandler(log_file)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s[%(levelname)s] %(name)s : %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)
logging.getLogger('requests.packages.urllib3.connectionpool').propagate = False

#данные для подключения к mongo (основная БД)
db_port = 27017
db_host = 'localhost'
db_name = 'vk'
db_user = '4ikist'
db_password = 'sederfes'

#данные для подключения redis (связи)
redis_host = '127.0.0.1'
redis_port = 6379
redis_batch_size = 185000

#dictionaries for pymorphy
dicts_path = os.path.join(os.path.dirname(__file__), 'dicts', 'ru', 'morphs.pickle')

queue_host = 'localhost'
queue_name = 'sn_queue'

#место где лежит прокси лист
local_proxy_list = os.path.join(os.path.dirname(__file__), 'proxy_list')


###############################################
#время в течении которого не будет обновлятся данные в БД (в секундах)
user_cache_time = 3600 * 24 * 7
message_cache_time = 3600 * 24
relation_cache_time = 3600 * 24 * 7
#время через которое будет обновлятся информация о пользователе (tracker)
update_iteration_time = 3600 * 24 * 7

#
