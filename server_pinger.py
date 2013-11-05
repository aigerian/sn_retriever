__author__ = '4ikist'
import logging

from contrib.db_connector import queue_handler
import threading
import time
import properties

log = logging.getLogger('server')


class PingerManager(threading.Thread):
    def __init__(self):
        super(PingerManager, self).__init__()
        self.queue_handler = queue_handler()
        self.log = logging.getLogger('server pinger')

    def run(self):
        while True:
            #clearing targets
            workers = self.queue_handler.get_bad_workers()
            if len(workers):
                self.log.info('updating bad workers %s' % workers)
                self.queue_handler.update_bad_targets(workers)
                self.queue_handler.remove_db_workers(workers)

            time.sleep(properties.STATUS_REFRESH_PERIOD_SEC)


def start_server_pinger():
    pm = PingerManager()
    pm.start()


