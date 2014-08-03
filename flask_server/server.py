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
    identity = server_helper.form_user(screen_name)
    return jsonify(identity=identity, success=True)


@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    identity = server_helper.retrieve_search_result(query=query)
    if not identity:
        return jsonify(success=False)
    return jsonify(identity=identity, success=True)


@app.route('/check_status/<identity>', methods=['GET'])
def check_status(identity):
    result = server_helper.is_ready(identity)
    log.info('check status for: %s; status is: %s'%(identity,result))

    return jsonify(is_ended=result, success=True)


@app.route("/get_user_result/<identity>", methods=['GET'])
def get_user_result(identity):
    result = server_helper.get_user_result(identity)
    return jsonify(result)


@app.route("/get_search_result/<identity>", methods=['GET'])
def get_search_result(identity):
    result, next = server_helper.get_search_result(identity)
    return jsonify(result=result, identity_next=next, success=True)


if __name__ == '__main__':
    app.run(threaded=True)