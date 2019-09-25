from flask import jsonify, Blueprint, send_file
from apiserver.blueprints.home.models import ODB
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

@home.route('/return-files/', methods=['POST'])
def return_files_tut():
    '''
    TODO make this for exporting graphs into CSV
    :return:
    '''
    return send_file('/var/www/PythonProgramming/PythonProgramming/static/images/python.jpg', attachment_filename='python.jpg')


