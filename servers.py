import time
from contrib.queue import QueueServer

__author__ = '4ikist'

if __name__ == '__main__':
    server1 = QueueServer()
    server2 = QueueServer()

    counter = 0
    while True:
        for i in range(100):
            server1.send_message({'method': 'test', 'params': 'None1', 'sn': 'test sn', 'counter': counter}, priority=1)
        for j in range(10):
            server2.send_message({'method': 'test', 'params': 'None2', 'sn': 'test sn', 'counter': counter}, priority=2)
        time.sleep(1)
        counter += 1
