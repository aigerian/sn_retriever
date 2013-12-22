import logging

__author__ = '4ikist'
from flask import Flask, render_template, jsonify, request

from contrib.queue import QueueServer
from contrib.db.mongo_db_connector import db_handler
import server_helper


app = Flask(__name__, static_folder='static', static_url_path='')
db = db_handler()
queue = QueueServer()

log = logging.getLogger('flask_server')
cache = {}
search_states = {}


@app.route('/')
def main():
    return render_template('search.html')


@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('q')
    if not query:
        return jsonify(success='false', details='bad params')

    if not request.form.get('ttr') and not request.form.get('fb') and not request.form.get('vk'):
        return jsonify(success='false', details='choose at least one of the social net')

    search_id = request.form.get('search_id')
    result = {}
    if request.form.get('ttr'):
        log.info('search in ttr %s' % query)
        result['ttr'] = queue.send_message(message={'sn': 'ttr', 'method': 'search', 'params': {'q': query}})
    if request.form.get('fb'):
        log.info('search in fb %s' % query)
        result['fb'] = queue.send_message(message={'sn': 'fb', 'method': 'search', 'params': {'q': query}})
    if request.form.get('vk'):
        log.info('search in vk %s' % query)
        result['vk'] = queue.send_message(message={'sn': 'vk', 'method': 'search', 'params': {'q': query}})

    search_states[unicode(search_id)] = result

    return jsonify(success='true')


@app.route('/search_result/<search_id>', methods=['POST'])
def get_search_result(search_id):
    sr_ids = search_states.get(search_id)
    if not sr_ids:
        return jsonify(success='false')

    result = {}
    for k, v in sr_ids.iteritems():
        result_el = queue.get_response(v)
        if not result_el:
            return jsonify(success='true', ended='false')
        else:
            result[k] = result_el
    return jsonify(success='true', ended='true', result=result, search_id=search_id)


@app.route('/process_search/<search_id>', methods=['POST'])
def process_search_result(search_id):
    result = cache.pop(search_id, None)
    if result:
        server_helper.process_search_result(result)
        return jsonify(success='true')
    else:
        return jsonify(success='false')


@app.route('/users', methods=['GET'])
def get_users():
    users = db.get_users()
    return render_template('users.html', users=users)


@app.route('/users/<int:user_id>')
def get_user(user_id):
    user = db.get_user(user_id)
    return render_template('user.html', user=user)


if __name__ == '__main__':
    app.run(threaded=True)