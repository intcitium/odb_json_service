from flask import jsonify, Blueprint, request
from apiserver.blueprints.osint.models import OSINT
from apiserver.utils import get_request_payload

osint = Blueprint('osint', __name__)
osintserver = OSINT()
osintserver.open_db()
osintserver.check_base_book()


@osint.route('/osint', methods=['GET'])
def index():

    return jsonify({
        "status": 200,
        "message": "Welcome. Basic stats of the endpoint database",
        "data": {'channels': ['ACLED']}
    })


@osint.route('/osint/acled', methods=['GET'])
def acled():

    return jsonify({
        "status": 200,
        "message": "Results from Armed Conflict Location Event Database (ACLED)",
        "data": osintserver.get_acled()
    })


@osint.route('/osint/ucdp', methods=['GET'])
def ucdp():

    return jsonify({
        "status": 200,
        "message": "Results from Uppsala Conflict Data Program",
        "data": osintserver.get_ucdp()
    })


@osint.route('/osint/twitter', methods=['GET'])
def twitter():


    return jsonify({
        "status": 200,
        "message": "Results from Twitter API",
        "data": osintserver.get_twitter(**(get_request_payload(request)))
    })
