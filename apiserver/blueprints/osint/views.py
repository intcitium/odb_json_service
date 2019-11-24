from flask import jsonify, Blueprint, request
from apiserver.blueprints.osint.models import OSINT
from apiserver.utils import get_request_payload
from flask_cors import CORS

osint = Blueprint('osint', __name__)
osintserver = OSINT()
osintserver.open_db()
osintserver.check_base_book()
osintserver.fill_db()
try:
    osintserver.create_indexes()
except Exception as e:
    if "attackpattern.search_fulltext already exists" in str(e):
        pass
    else:
        print(str(e))
CORS(osint)


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

    results, message = osintserver.get_twitter(**(get_request_payload(request)))
    return jsonify({
        "status": 200,
        "message": message,
        "data": results
    })


@osint.route('/osint/geo_spatial_view', methods=['GET'])
def geo_spatial_view():

    results, message = osintserver.geo_spatial_view(**(get_request_payload(request)))
    return jsonify({
        "status": 200,
        "message": message,
        "data": results
    })

@osint.route('/osint/save', methods=['POST'])
def save():
    payload = get_request_payload(request)
    if payload:
        case, message = osintserver.save_osint(**payload)
        return jsonify({
            "status": 200,
            "message": message,
            "data": case
        })
    else:
        return jsonify({
            "status": 503,
            "message": "Error saving structure of graph received.",
            "data": None
        })


@osint.route('/osint/merge_nodes', methods=['POST'])
def merge_nodes():
    '''
    Base route for merging nodes
    :return:
    '''
    r = get_request_payload(request)
    return jsonify({
        "status": 200,
        "message": "Nodes merged",
        "data": osintserver.merge_osint(**r)
    })

@osint.route('/osint/get_suggestion_items', methods=['POST'])
def get_suggestion_items():
    '''
    Base route for merging nodes
    :return:
    '''
    r = get_request_payload(request)
    return jsonify({
        "status": 200,
        "message": "Search conducted",
        "data": osintserver.get_suggestion_items(**r)
    })


@osint.route('/osint/cve', methods=['GET'])
def cve():
    '''
    Base route for merging nodes
    :return:
    '''
    return jsonify({
        "status": 200,
        "message": "Database updated with latest CVE",
        "data": osintserver.cve()
    })


@osint.route('/osint/poisonivy', methods=['GET'])
def poisonivy():
    '''
    Base route for merging nodes
    :return:
    '''
    return jsonify({
        "status": 200,
        "message": "Database updated with latest CVE",
        "data": osintserver.poisonivy()
    })

@osint.route('/osint/get_latest_cti', methods=['GET'])
def get_latest_cti():
    '''
    Base route for merging nodes
    :return:
    '''
    return jsonify({
        "status": 200,
        "message": "Database updated with latest CVE",
        "data": osintserver.run_otx()
    })
