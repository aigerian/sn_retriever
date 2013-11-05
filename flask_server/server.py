import time

__author__ = '4ikist'

from flask import Flask, render_template, jsonify, request

from contrib.db_connector import db_handler, queue_handler
import server_helper
app = Flask(__name__, static_folder='static', static_url_path='')
db = db_handler()
queue = queue_handler()


@app.route('/')
def main():
    return render_template('search.html')


@app.route('/search', methods=['POST'])
def search():
    search_target_root = 'search_%s' % (time.time())
    query = request.form.get('q')
    if not query:
        return jsonify(success='false', details='bad params')
    if request.form.get('ttr'):
        queue.create_new_target(target={'sn': 'ttr', 'method': 'search', 'params': {'q': query}},
                                root=search_target_root)
    if request.form.get('fb'):
        queue.create_new_target(target={'sn': 'fb', 'method': 'search', 'params': {'q': query}},
                                root=search_target_root)
    if request.form.get('vk'):
        queue.create_new_target(target={'sn': 'vk', 'method': 'search', 'params': {'q': query}},
                                root=search_target_root)
    result = queue.get_target_result(search_target_root)
    print result
    return jsonify(success='true', target_root=search_target_root, result=result)


@app.route('/process_search/<search_target_root>', methods=['POST'])
def process_search_result(search_target_root):
    result = queue.get_target_result(search_target_root)
    server_helper.process_search_result(result)
    return jsonify(success='true')


@app.route('/users', methods=['GET'])
def get_users():
    users = db.get_users()
    return render_template('users.html', users=users)


@app.route('/users/<int:user_id>')
def get_user(user_id):
    user = db.get_user(user_id)
    return render_template('user.html',user=user)


if __name__ == '__main__':
    import server_pinger

    server_pinger.start_server_pinger()
    app.run()