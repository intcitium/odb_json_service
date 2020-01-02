from flask import jsonify, Blueprint, request
from apiserver.blueprints.users.models import userDB
from apiserver.blueprints.home.models import get_datetime
from apiserver.utils import get_request_payload
import click

# Application Route specific object instantiation
users = Blueprint('users', __name__)
# Case where no DB has been established from which the message returned should let the user know to run the setup API

odbserver = userDB()
init_required = odbserver.open_db()
if init_required:
    click.echo("[%s_User_init] Setup required" % get_datetime())
else:
    odbserver.open_db()
    odbserver.check_standard_users()
    click.echo('[%s_UserServer_init] Complete' % (get_datetime()))


@users.route('/users/db_init', methods=['GET'])
def db_init():
    """
    API endpoint used when the DB has not been created
    :return:
    """
    result = odbserver.create_db()
    if not result:
        return jsonify({
            "status": 200,
            "message": "Users database already exists"
        })
    else:
        message = odbserver.check_standard_users()
        return jsonify({
            "status": 200,
            "message": "Users database %s" % message
        })


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
            "activity": auth['activity'],
            "users": auth['users']
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

    users = odbserver.get_users_nodes()
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

@users.route('/users/get_users', methods=['GET'])
def get_users():

    users = odbserver.get_users()
    return jsonify({
        "status": 200,
        "message": "Found %d users" % len(users),
        "data": users
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


@users.route('/users/get_messages', methods=['GET'])
def get_messages():
    r = get_request_payload(request)
    if r and 'userName' in r.keys():
        data = odbserver.get_messages(userName=r['userName'])
        return jsonify({
            "status": 200,
            "message": data['message'],
            "data": data
        })
    else:
        return jsonify({
            "status": 200,
            "message": "Failed to process request",
            "data": None
        })


@users.route('/users/read_message', methods=['POST'])
def read_message():
    r = get_request_payload(request)
    if r and 'userKey' in r.keys() and 'msgKey' in r.keys():
        data = odbserver.read_message(userKey=r['userKey'], msgKey=r['msgKey'])
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
