import logging

__author__ = '4ikist'

import uuid
import json

import pika

import properties


__doc__ = """
QueueServer - class which objects can send some rpc calls for workers throw rabbitMQ queue
QueueWorker - class which objects can processing this messages

message structure must be hash objects which contains:

sn - social net name
method - method of api name
params - params of method


result of processing must be
success - True or False
data - data or detail if success == False

or None - if requests are overflow

"""
MAX_PRIORITY = 0
EMPTY_BODY = 'EMPTY_BODY'


class QueueServer(object):
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=properties.queue_host))
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue
        self.channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue)
        self.log = logging.getLogger('QServer')
        self.queue = {}
        self.processed_queue = {}


    def on_response(self, ch, method, props, body):
        exist_body = self.queue.pop(props.correlation_id, None)
        if exist_body == EMPTY_BODY:
            self.log.info('getting response from client: \n%s' % body)
            self.processed_queue[props.correlation_id] = body


    def send_message(self, message, priority=MAX_PRIORITY):
        self.response = None
        corr_id = str(uuid.uuid4())
        self.queue[corr_id] = EMPTY_BODY
        self.log.info('sending message with corr_id %s' % corr_id)
        self.channel.basic_publish(exchange='',
                                   routing_key=properties.queue_name,
                                   properties=pika.BasicProperties(reply_to=self.callback_queue,
                                                                   correlation_id=corr_id,
                                                                   priority=priority),
                                   body=json.dumps(message))
        return corr_id

    def get_response(self, corr_id):
        body = self.processed_queue.pop(corr_id, None)
        if body and body != EMPTY_BODY:
            return json.loads(body).get('data')
        else:
            self.log.info('processed queue cannot contain this corr_id %s' % corr_id)
            return None

    def wait_response(self, corr_id):
        while True:
            result = self.get_response(corr_id)
            if result:
                return result


class QueueWorker(object):
    def __init__(self, function):
        self.function = function
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=properties.queue_host))
        self.channel = connection.channel()
        self.channel.queue_declare(queue=properties.queue_name)
        self.log = logging.getLogger('QClient')

    def on_request(self, ch, method, props, body):
        self.log.info('getting request from server: \n%s' % body)
        message = json.loads(body)
        response = self.function(message)
        self.log.info('request processed: \n%s' % response)
        if not response:
            return

        ch.basic_publish(exchange='',
                         routing_key=props.reply_to,
                         properties=pika.BasicProperties(correlation_id=props.correlation_id),
                         body=json.dumps(response))

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def start(self):
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(self.on_request, queue=properties.queue_name)
        try:
            self.channel.start_consuming()
        except Exception as e:
            self.channel.stop_consuming()
            self.log.exception(e)


