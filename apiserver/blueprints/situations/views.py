from flask import jsonify, Blueprint, request
from apiserver.blueprints.users.views import odbserver
from apiserver.blueprints.simulations.views import simserver

situations = Blueprint('situations', __name__)


@situations.route('/situations', methods=['GET'])
def index():

    return jsonify({
        "status": 200,
        "message": "Situations Base URL",
        "data": odbserver.get_db_stats()
    })


@situations.route('/situations/get_risks', methods=['GET'])
def get_risks():





    return jsonify({
        "status": 200,
        "message": "Situations Base URL",
        "replies": [
            {
              "type": "text",
              "content": "Hello world!"
            }],
        "conversation": {
            "language": "en",
            "memory": {
              "user": "Bob"
            }
          }
    })

