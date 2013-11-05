import random
import time

__author__ = '4ikist'

import logging
import sys, os
import threading

from contrib.connect import VK_API, FB_API, TTR_API
from contrib.db_connector import queue_handler

import properties


client_name = 'Client%s' % (random.randint(0, 1000))
log = logging.getLogger('WORKER')


class Pinger(threading.Thread):
    def __init__(self, client_name=client_name):
        super(Pinger, self).__init__()
        self.client_name = client_name
        self.queue_handler = queue_handler()
        self.log = logging.getLogger('client pinger')

    def run(self):
        while True:
            self.queue_handler.set_worker_status(self.client_name)
            time.sleep(properties.STATUS_REFRESH_PERIOD_SEC)


class Worker(threading.Thread):
    def __init__(self, client_name=client_name):
        super(Worker, self).__init__()
        log.info('starting worker')
        self.queue_handler = queue_handler()
        self.client_name = client_name
        log.info('initializing apis')
        self.apis = {'vk': VK_API(), 'fb': FB_API(), 'ttr': TTR_API()}

    def run(self):
        while True:
            target = self.queue_handler.get_new_target(self.client_name)
            target_body = target['body']
            api = self.apis[target_body['sn']]

            log.info(
                'processing result method: %s, params: %s, sn: %s' % (
                    target_body['method'], target_body['params'], target_body['sn']))
            try:
                target_result = getattr(api, target_body['method'])(**target_body['params'])
            except Exception as e:
                log.error('exception %s with result method: %s, params: %s, sn: %s' % (
                    e, target_body['method'], target_body['params'], target_body['sn']))
                target_result = {'error': True}
            result_id = self.queue_handler.add_result(target_result, target_body['sn'])
            self.queue_handler.resolve_target(target['_id'], result_id)


if __name__ == '__main__':
    client_name = '%s_%s' % (os.environ['COMPUTERNAME'], int(time.time()))
    pinger = Pinger(client_name=client_name)
    pinger.start()

    worker = Worker(client_name=client_name)
    worker.start()


