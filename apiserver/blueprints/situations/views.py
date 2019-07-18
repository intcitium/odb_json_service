from flask import jsonify, Blueprint, request
from apiserver.blueprints.users.views import odbserver
from apiserver.blueprints.situations.models import SituationsDB
import click

situations = Blueprint('situations', __name__)
SDB = SituationsDB()
SDB.open_db()

@situations.route('/situations', methods=['GET'])
def index():

    return jsonify({
        "status": 200,
        "message": "Situations Base URL",
        "data": odbserver.get_db_stats()
    })


@situations.route('/situations/get_risks', methods=['POST'])
def get_risks():
    r = request.form.to_dict(flat=True)
    click.echo("RECEIVED %s" % r)
    if 'LastName' in r.keys():
        replyContent = SDB.model_message(SDB.get_risks(r['LastName']))

    return jsonify({
        "status": 200,
        "message": "Situations Base URL",
        "replies": [
            {
              "type": "text",
              "content": replyContent
            }],
        "conversation": {
            "language": "en",
            "memory": {
              "user": "Bob"
            }
          }
    })

