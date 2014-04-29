import time
from birdy.twitter import UserClient, TwitterRateLimitError
from contrib.api.ttr import TTR_API
from contrib.db.database_engine import Persistent
import properties

__author__ = '4ikist'


def test_ttr():
    api = TTR_API()
    sr = api.search('medvedev')
    for el in sr:
        print el
if __name__ == '__main__':
    test_ttr()