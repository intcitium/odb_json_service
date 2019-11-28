import json
from flask import jsonify, Blueprint, send_file, request
from apiserver.blueprints.home.models import ODB
from apiserver.utils import get_request_payload, allowed_file, check_for_file
from werkzeug.utils import secure_filename
# Application Route specific object instantiation
home = Blueprint('home', __name__)
odbserver = ODB()
odbserver.open_db()


@home.route('/', methods=['GET'])
def index():

    return jsonify({
        "status": 200,
        "message": "Welcome. Basic stats of the endpoint database",
        "data": odbserver.get_db_stats()
    })


@home.route('/snapshot', methods=['GET'])
def get_snapshot():

    return jsonify({
        "status": 200,
        "message": "Sample data from the file system",
        "data": odbserver.get_data()
    })


@home.route('/merge_nodes', methods=['POST'])
def merge_nodes():
    '''
    Base route for merging nodes
    :return:
    '''
    r = get_request_payload(request)
    return jsonify({
        "status": 200,
        "message": "Nodes merged",
        "data": odbserver.merge_nodes(request)
    })


@home.route('/return-files/', methods=['POST'])
def return_files_tut():
    '''
    TODO make this for exporting graphs into CSV
    :return:
    '''
    return send_file('/var/www/PythonProgramming/PythonProgramming/static/images/python.jpg', attachment_filename='python.jpg')


@home.route('/graph_etl_model', methods=['POST'])
def graph_etl_model():
    """
    If only a file is received and a mapping is not required the request is focused on the file
    If there is only a filename, the service expects that filename to be in the directory and that a model
    will be used on that file for changing into a graph
    :return:
    """
    r = get_request_payload(request)
    file = check_for_file(request, odbserver)
    if not file["data"]:
        if "file" in request.form.to_dict().keys():
            graph = odbserver.graph_etl_model(
                json.loads(request.form.to_dict()['model']),
                odbserver.file_to_frame(request.form.to_dict()["file"])["data"])
        elif "file" in r.keys() and "model" in r.keys():
            graph = odbserver.graph_etl_model(r["model"], r["file"])
        else:
            return jsonify(file)
    else:
        graph = odbserver.graph_etl_model(
            json.loads(request.form.to_dict()['model']),
            file["data"])
    return jsonify({
        "status": 200,
        "data": graph,
        "filename": file["data"]
    })


@home.route('/file_to_graph', methods=['POST'])
def file_to_graph():

    file = check_for_file(request, odbserver)
    if not file["data"]:
        return jsonify(file)
    else:
        graph = odbserver.file_to_graph(file["data"])
        return jsonify({
            "status": 200,
            "data": graph,
            "filename": file["data"]
        })

@home.route('/refresh_hier', methods=['GET'])
def refresh_hier():
    graph = odbserver.file_to_graph("eppm_hier.xlsx")
    return jsonify({
        "status": 200,
        "data": graph
    })
