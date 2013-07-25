"""
file for properties
"""
__author__ = '4ikist'

import logging
import os


#ttr application credentials
ttr_consumer_key = 'VbDKb4QMLwe5YsdHESNFOg'
ttr_consumer_secret = 'cEaSWdxHnQ6I3sGYaIBufjahyDsAP0SY5lx1YCI'
ttr_access_token = '612776846-ZC55TSeiCvufmggMVz9ZKpbQFXodTXuA9JSq9Vee'
ttr_access_token_secret = 'kxm2cuq9xNaSUBKPxIlUNJI3wKJ57VHmT0h1w1PuLWE'

#vk application credentials
vk_key = 'mRNxuLGPrSCtuqLl9DkU'
vk_app_name = 'vk_retr'

vk_login = '+79138973664'
vk_pass = 'sederfes'

#vk helper...
vk_access_credentials = {'client_id': '3784486',
                         'scope': 'friends,photos,audio,video,docs,notes,pages,status,offers,questions,wall,groups',
                         'redirect_uri': 'https://oauth.vk.com/blank.html',
                         'display': 'mobile',
                         'v': '4.104',
                         'response_type':'token'}
#also...
vk_edit_app_url = 'https://vk.com/editapp?id=3784486&section=options'



#log file
log_file = os.path.join(os.path.dirname(__file__), 'result.log')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
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
db_port = 10060
db_host = 'alex.mongohq.com'
db_name = 'ttr'
db_user = '4ikist'
db_password = 'sederfes'

#db_connection (mongo lab)
# db_port = 37518
# db_host = 'ds037518.mongolab.com'
# db_name = 'ttr'
# db_user = '4ikist'
# db_password = 'sederfes'

