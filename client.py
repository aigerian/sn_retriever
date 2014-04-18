import random
import time
from contrib.api.entities import APIException, APIRequestOverflowException
from contrib.api.fb import FB_API
from contrib.api.ttr import TTR_API
from contrib.api.vk import VK_API

__author__ = '4ikist'

import logging
import os


from contrib.queue import QueueWorker


log = logging.getLogger('WORKER')
client_name = '%s_%s' % (os.environ['COMPUTERNAME'], int(time.time()))


class Worker(object):
    def __init__(self, client_name=client_name):
        log.info('starting worker %s' % client_name)
        self.queue_handler = QueueWorker(self.process)
        self.client_name = client_name
        log.info('initializing apis')
        self.apis = {'vk': VK_API(), 'fb': FB_API(), 'ttr': TTR_API()}

    def process(self, message):
        sn = message.get('sn')
        api = self.apis.get(sn)
        if not api:
            return {'success': False, 'data': 'i haven"t this api! '}
        method = message.get('method')
        params = message.get('params')
        log.info('processing message from server [%s] [%s] [%s]' % (sn, method, params))
        try:
            result_data = getattr(api, method)(**params)
            result = {'success': True, 'data': result_data}
            log.info('message was processed')
        except APIRequestOverflowException:
            time.sleep(3600)
            return None
        except APIException as e:
            return {'success': False, 'data': e}
        except Exception as e:
            log.exception(e)
            return {'success': False, 'data': 'we have some problem! [%s]' % e}
        return result

    def start(self):
        self.queue_handler.start()


if __name__ == '__main__':
    worker = Worker()
    worker.start()


