import os
from flask import jsonify, Blueprint, send_file, request
from apiserver.blueprints.home.models import ODB
from apiserver.utils import get_request_payload, allowed_file
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


@home.route('/file_to_graph', methods=['POST'])
def file_to_graph():

    if "file" not in request.files:
        keys = ""
        for k in request.files.keys():
            keys+=k + ","

        return jsonify({
            "status": 200,
            "message": "No file parts found. Ensure 'file' is within the keys of the payload sent. Found: %s" % keys,
            "data": None
        })
    else:
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "status": 200,
                "message": "No filename found for the selection.",
                "data": None
            })
        else:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(odbserver.datapath, filename))
                graph = odbserver.file_to_graph(filename)
                return jsonify({
                    "status": 200,
                    "data": graph,
                    "filename": filename
                })
            else:
                return jsonify({
                    "status": 200,
                    "message": "File extension not allowed",
                    "data": file.filename,
                })
