import threading
from collections import deque
import uuid
from contrib.api.ttr import get_api

__author__ = '4ikist'


class Worker(threading.Thread):
    def __init__(self, api_method, **kwargs):
        super(Worker, self).__init__()
        self.method = api_method
        self.method_kwargs = kwargs
        self.result_object = None

    def run(self):
        print self.method_kwargs
        result = self.method(**self.method_kwargs)
        self.result_object = result
        print 'ready!\n%s\n%s' % (self.method, self.result_object)

    @property
    def result(self):
        return self.result_object


class ThreadHandler(object):
    def __init__(self):
        self.workers = {}

    def call(self, method, **kwargs):
        w = Worker(method, **kwargs)
        w.start()
        identity = str(uuid.uuid1())
        self.workers[identity] = w
        return identity

    def is_ready(self, identity):
        w = self.workers.get(identity)
        if not w:
            raise Exception('not found worker %s' % identity)
        return not w.isAlive()

    def get_result(self, identity):
        if not self.is_ready(identity):
            return None
        worker = self.workers.get(identity)
        result = worker.result
        del self.workers[identity]
        return result


if __name__ == '__main__':
    h = ThreadHandler()
    identity = h.call(get_api().get_user, screen_name='@linoleum2k12')
    print h.is_ready(identity)
    print h.is_ready(identity)
    print h.is_ready(identity)
