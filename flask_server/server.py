from contrib.api.entities import APIUser
from contrib.api.threading.api_threads import ThreadHandler
from contrib.api.ttr import get_api
from flask_server.server_helper import ServerHelper

__author__ = '4ikist'
from flask import Flask, render_template, jsonify, request

from contrib.db.database_engine import Persistent
from properties import logger

app = Flask(__name__, static_folder='static', static_url_path='')

server_helper = ServerHelper(Persistent(), get_api())

log = logger.getChild('web')

search_cache = {}


@app.route('/')
def main():
    return render_template('search.html')


@app.route('/retrieve_user', methods=['POST'])
def retrieve_user():
    screen_name = request.form.get('screen_name')
    user_options
    if user:
        return jsonify(user_id=user.get('_id'), success=True)

    identity = api_th.call(get_api().get_user, screen_name=screen_name)
    return jsonify(identity=identity, success=True)


@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')

    return jsonify(identity=identity, success=True)


@app.route('/check_status/<identity>', methods=['POST'])
def check_status(identity):
    result = api_th.is_ready(identity)
    return jsonify(is_ended=result, success=True)


@app.route('/get_result/<identity>', methods=['POST'])
def get_result(identity):
    result = api_th.get_result(identity)
    if isinstance(result, APIUser):
        persistent.save_user(result)
        return jsonify(user_id=result.get('_id'), success=True)


if __name__ == '__main__':
    app.run(threaded=True)