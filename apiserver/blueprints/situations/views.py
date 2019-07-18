from flask import jsonify, Blueprint, request
from apiserver.blueprints.users.views import odbserver
from apiserver.blueprints.situations.models import SituationsDB, FirstName, LastName, DateOfBirth, PlaceOfBirth
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

    risks = None # Placeholder for the query results
    r = request.form.to_dict(flat=True)
    click.echo(r)
    click.echo(request.args)
    click.echo(request.get_data())
    if LastName in r.keys():
        searchType = LastName
        risks = SDB.get_risks(r[searchType])
    elif FirstName in r.keys():
        searchType = FirstName
    elif DateOfBirth in r.keys():
        searchType = DateOfBirth
    elif PlaceOfBirth in r.keys():
        searchType = PlaceOfBirth
    else:
        searchType = r[r.keys(0)]
    if risks:
        replyContent = SDB.model_message(risks)
    else:
        replyContent = "Sorry, I couldn't find anyone with the %s %s" % (searchType, r[searchType])

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

