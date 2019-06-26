from flask import jsonify, Blueprint, request
from apiserver.blueprints.users.views import odbserver

situations = Blueprint('situations', __name__)

@situations.route('/situations', methods=['GET'])
def index():

    return jsonify({
        "status": 200,
        "message": "Welcome. Basic stats of the endpoint database",
        "data": odbserver.get_db_stats()
    })
