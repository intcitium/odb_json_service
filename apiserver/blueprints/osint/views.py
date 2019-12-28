from flask import jsonify, Blueprint, request
from apiserver.blueprints.osint.models import OSINT
from apiserver.utils import get_request_payload
from flask_cors import CORS
from apiserver.blueprints.osint.shodan import Shodan

osint = Blueprint('osint', __name__)
shodanserver = Shodan()
shodanserver.open_db()
osintserver = OSINT()
osintserver.open_db()
osintserver.refresh_indexes()
#osintserver.check_base_book()
#osintserver.fill_db()
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


@osint.route('/osint/shodan', methods=['GET'])
def shodan():

    results, message = shodanserver.search(**(get_request_payload(request)))
    return jsonify({
        "status": 200,
        "message": message,
        "data": results
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

    message = osintserver.get_twitter(**(get_request_payload(request)))
    return jsonify({
        "status": 200,
        "message": message
    })

@osint.route('/osint/twitter/associates', methods=['GET'])
def get_associates():

    results = osintserver.get_associates(**(get_request_payload(request)))
    return jsonify({
        "status": 200,
        "message": results
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


@osint.route('/osint/get_neighbors', methods=['POST'])
def get_neighbors():
    '''
    Base route for merging nodes
    :return:
    '''
    r = get_request_payload(request)
    r = osintserver.get_neighbors(**r)
    return jsonify({
        "status": 200,
        "message": r["message"],
        "data": r["data"]
    })

@osint.route('/osint/get_neighbors_index', methods=['POST'])
def get_neighbors_index():
    '''
    Base route for merging nodes
    :return:
    '''
    r = get_request_payload(request)
    r = osintserver.get_neighbors_index(**r)
    return jsonify({
        "status": 200,
        "message": r["message"],
        "data": r["data"]
    })

@osint.route('/osint/cve', methods=['GET'])
def get_cve():
    '''
    Base route for merging nodes
    :return:
    '''
    return jsonify({
        "status": 200,
        "message": "Database updated with latest CVE",
        "data": osintserver.get_cve()
    })


@osint.route('/osint/poisonivy', methods=['GET'])
def poisonivy():
    """
    Get the latest dump from the CTI url. The current URL is set to oasis github which delivers a small sample
    using the STIX model. The expected JSON from the URL is in a format of nodes with STIX 12 entity types and
    edges including relationships and sightings. The function calls graph_poisonivy to extract the JSON into a
    graph form and returns a message prior to starting that thread.
    nodes:
        "type": "campaign",
        "id": "campaign--8e2e2d2b-17d4-4cbf-938f-98ee46b3cd3f",
        "created": "2016-04-06T20:03:00.000Z",
        "name": "Green Group Attacks Against Finance",
        "description": "Campaign by Green Group against targets in the financial services sector."
    edges:

        "type": "sighting",
        "id": "sighting--ee20065d-2555-424f-ad9e-0f8428623c75",
        "created_by_ref": "identity--f431f809-377b-45e0-aa1c-6a4751cae5ff",
        "created": "2016-04-06T20:08:31.000Z",
        "modified": "2016-04-06T20:08:31.000Z",
        "sighting_of_ref": "indicator--8e2e2d2b-17d4-4cbf-938f-98ee46b3cd3f"

    :return:
    """
    return jsonify({
        "status": 200,
        "message": osintserver.get_poisonivy(),
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

@osint.route('/osint/start_twitter_monitor', methods=['GET'])
def start_twitter_monitor():
    '''
    Base route for merging nodes
    :return:
    '''
    r = osintserver.start_twitter_monitor()
    return jsonify({
        "status": 200,
        "message": r["message"]
    })

@osint.route('/osint/start_merge_monitor', methods=['GET'])
def start_merge_monitor():
    '''
    Base route for merging nodes
    :return:
    '''
    r = osintserver.start_merge_monitor()
    return jsonify({
        "status": 200,
        "message": r["message"]
    })


@osint.route('/osint/create_monitor', methods=['POST'])
def create_monitor():
    r = get_request_payload(request)
    if r and 'userName' in r.keys():
        message = osintserver.create_monitor(**r)
        return jsonify({
            "status": 200,
            "message": message
        })
    else:
        return jsonify({
            "status": 200,
            "message": "Failed to process request",
            "data": None
        })

@osint.route('/osint/get_user_monitor', methods=['POST'])
def get_user_monitor():
    r = get_request_payload(request)
    if r and 'userName' in r.keys():
        d = osintserver.get_user_monitor(**r)
        return jsonify({
            "status": 200,
            "message": d["message"],
            "data": d["data"]
        })
    else:
        return jsonify({
            "status": 200,
            "message": "Failed to process request",
            "data": None
        })

@osint.route('/osint/search', methods=['POST'])
def search():
    r = get_request_payload(request)
    if r and 'search' in r.keys():
        search = osintserver.search(**r)
        return jsonify({
            "status": 200,
            "message": search
        })
    else:
        return jsonify({
            "status": 200,
            "message": "Failed to process request",
            "data": None
        })
