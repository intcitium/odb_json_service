from flask import jsonify, Blueprint, request
from apiserver.blueprints.users.models import userDB
from apiserver.blueprints.home.models import get_datetime
from apiserver.utils import get_request_payload
import click
# Application Route specific object instantiation
users = Blueprint('users', __name__)
odbserver = userDB()
odbserver.open_db()
odbserver.check_standard_users()
click.echo('[%s_UserServer_init] Complete' % (get_datetime()))


@users.route('/users', methods=['GET'])
def index():

    return jsonify({
        "status": 200,
        "message": '''Users Endpoint:\n
        snapshot: Get sample data from the user file system
        delete: Remove a user from the system
        create: Register a new user with email and password
        login: User authorization access into the application
        logout: Blacklist a user's current session
        get: User activitiy
        message: Create a message from the user and a record of the transmission to other users
        confirm_email: Send a message for the user to confirm account validity through email
        confirm: Complete the process with the confirm_email token
        '''
    })


@users.route('/users/snapshot', methods=['GET', 'POST'])
def get_snapshot():

    if request.method == "POST":
        auth = odbserver.auth_user(request.headers['Authorization'])
        if auth:
            return jsonify(auth)
        else:
            return jsonify({
                "status": 200,
                "message": "Sample data from the file system",
                "data": odbserver.get_data()
            })
    else:
        return jsonify({
            "status": 200,
            "message": "Sample data from the file system",
            "data": odbserver.get_data()
        })


@users.route('/users/delete', methods=['POST'])
def delete():

    auth = odbserver.auth_user(request.headers['Authorization'])
    if auth:
        return jsonify(auth)
    else:
        results = odbserver.delete_user(request)
        if results['data']:
            return jsonify({
                "status": 201,
                "message": results['message'],
                "node": results['data']
            })
        else:
            return jsonify({
                "status": 409,
                "message": results['message']
            })


@users.route('/users/create', methods=['POST'])
def create():

    results = odbserver.create_user(request.form.to_dict(flat=True))
    if results:
        return jsonify({
            "status": 201,
            "message": results['message'],
            "node": results['data']
        })
    else:
        return jsonify({
            "status": 409,
            "message": "User exists"
        })


@users.route('/users/login', methods=['POST'])
def login():

    auth = odbserver.login(request)
    if auth['session']:
        return jsonify({
            "status": 200,
            "message": "User authenticated",
            "token": auth['token'],
            "sessionId": auth['session'],
            "activityGraph": auth['data']
        })
    else:
        return jsonify({
            "status": 204,
            "message": auth['message'],
            "data": str(auth)
        })


@users.route('/users/logout', methods=['POST'])
def logout():

    auth = odbserver.auth_user(request.headers['Authorization'])
    if auth:
        return jsonify(auth)
    else:
        auth = odbserver.logout(request)
        if auth:
            return jsonify({
                "status": 200,
                "message": auth
            })
        else:
            return jsonify({
                "status": 204,
                "message": auth
            })

@users.route('/users/get', methods=['POST'])
def get():

    auth = odbserver.auth_user(request.headers['Authorization'])
    if auth:
        return jsonify(auth)
    else:
        auth = odbserver.get_activity(request=request)
        if auth["data"]:
            return jsonify({
                "status": 200,
                "message": auth['message'],
                "data": auth["data"]
            })
        else:
            return jsonify({
                "status": 204,
                "message": auth["message"]
            })

@users.route('/users/get_user_nodes', methods=['GET'])
def get_user_nodes():

    users = odbserver.get_users()
    if users["data"]:
        return jsonify({
            "status": 200,
            "message": users['message'],
            "data": users["data"]
        })
    else:
        return jsonify({
            "status": 204,
            "message": "No users found"
            })

@users.route('/users/message', methods=['POST'])
def message():

    auth = odbserver.auth_user(request.headers['Authorization'])
    if auth:
        return jsonify(auth)
    else:
        auth = odbserver.send_message(request)
        if auth["data"]:
            return jsonify({
                "status": 200,
                "message": auth['message'],
                "data": auth["data"]
            })
        else:
            return jsonify({
                "status": 204,
                "message": auth["message"]
            })


@users.route('/users/confirm_email', methods=['POST'])
def confirm_email():
    form = request.form.to_dict()
    return jsonify(odbserver.confirm_user_email(email=form['email'], userName=form['userName']))


@users.route('/users/confirm/<token>')
def confirm(token):
    return jsonify(odbserver.confirm(token=token))

@users.route('/users/get_cases', methods=['GET'])
def get_cases():
    r = get_request_payload(request)
    if r and 'userName' in r.keys():
        data = odbserver.get_user_cases(userName=r['userName'])
        return jsonify({
            "status": 200,
            "message": data['message'],
            "data": data['data']
        })
    else:
        return jsonify({
            "status": 200,
            "message": "Failed to process request",
            "data": None
        })



