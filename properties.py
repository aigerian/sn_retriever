"""
file for properties
"""
__author__ = '4ikist'

import logging
import os, sys


def module_path():
    if hasattr(sys, "frozen"):
        return os.path.dirname(
            unicode(sys.executable, sys.getfilesystemencoding())
        )
    return os.path.dirname(unicode(__file__, sys.getfilesystemencoding()))


certs_path = os.path.join(module_path(), 'cacert.pem')

#facebook application credentials
fb_app_id = '182482928555387'
fb_app_secret = 'd8188882ccf227f3b1c1b2f31b7f4429'
fb_client_token = '655cffd14ae5a391b89197e3e5dc3e12'

fb_user_email = 'alexey.proskuryakov@gmail.com'
fb_user_pass = 'sederfes_fb#'

#ttr application credentials
ttr_consumer_key = 'VbDKb4QMLwe5YsdHESNFOg'
ttr_consumer_secret = 'cEaSWdxHnQ6I3sGYaIBufjahyDsAP0SY5lx1YCI'
ttr_access_token = '612776846-80PPCl8bpLD6hcXSHudaMEUajBrLHHE8b9d31Tzk'
ttr_access_token_secret = 'H9dfxvLnxT9HGw7PH2NQsBAKbup1qEgz81UrURqAeCkaA'

#vk application credentials
vk_key = 'mRNxuLGPrSCtuqLl9DkU'
vk_app_name = 'vk_retr'

vk_login = '+79811064022'
vk_pass = 'sederfes100500'

vk_fields = 'nickname, screen_name, sex, bdate, city, country, timezone, has_mobile, contacts, education, online, counters, relation, last_seen, status, universities'
#vk helper...
vk_access_credentials = {'client_id': '3784486',
                         'scope': 'friends,photos,audio,video,docs,notes,pages,status,offers,questions,wall,groups,messages',
                         'redirect_uri': 'https://oauth.vk.com/blank.html',
                         'display': 'mobile',
                         'v': '4.104',
                         'response_type': 'token'}
#also...
vk_edit_app_url = 'https://vk.com/editapp?id=3784486&section=options'


#log file
log_file = os.path.join(module_path(), 'result.log')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
fh = logging.FileHandler(log_file)
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s[%(levelname)s] %(name)s : %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

#retrieving parameters
cursor_iterations = 5

#db_connection (mongo hq)
#db_port = 10060
#db_host = 'alex.mongohq.com'
#db_name = 'ttr'
#db_user = '4ikist'
#db_password = 'sederfes'

db_port = 27772
db_host = 'localhost'
db_name = 'ttr'
db_user = '4ikist'
db_password = 'sederfes'

#db_connection (mongo lab)
# db_port = 37518
# db_host = 'ds037518.mongolab.com'
# db_name = 'ttr'
# db_user = '4ikist'
# db_password = 'sederfes'

#neo4j params
gdb_host = 'http://localhost:7474/db/data'
gdb_path = 'C:\Users\4ikist\Documents\Neo4j\default.graphdb'
#dictionaries for pymorphy
dicts_path = os.path.join(os.path.dirname(__file__), 'dicts', 'ru', 'morphs.pickle')

queue_host = 'localhost'
queue_name = 'sn_queue'
