from datetime import datetime
from contrib.api.ttr import TTR_API, get_api
from contrib.core.tracking import TTR_Tracking
from contrib.db.database_engine import Persistent
import numpy as np

__author__ = '4ikist'
if __name__ == '__main__':
    api = get_api()
    users = api.get_users_info(ids=[14582075,2482639454L])
    for el in users:
        print el