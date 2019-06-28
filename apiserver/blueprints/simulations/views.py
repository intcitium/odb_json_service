from flask import jsonify, Blueprint, request, json
from apiserver.blueprints.users.views import odbserver as OAuth
from apiserver.blueprints.simulations.models import Pole
import click

simulations = Blueprint('simulations', __name__)
simserver = Pole()
simserver.open_db()


@simulations.route('/simulations', methods=['GET'])
def index():

    return jsonify({
        "status": 200,
        "message": '''Simulations Endpoint
        
        '''
    })


@simulations.route('/simulations/create_family', methods=['POST'])
def create_family():
    auth = OAuth.auth_user(request.headers['Authorization'])
    if auth:
        return jsonify(auth)
    else:
        if 'LastName' in request.form.to_dict().keys():
            family = simserver.create_family(LastName=request.form.to_dict()['LastName'])
        else:
            family = simserver.create_family()
        return jsonify({
            "status": 200,
            "message": family['message'],
            "data": family['data']
        })

@simulations.route('/simulations/run', methods=['POST'])
def run():
    auth = OAuth.auth_user(request.headers['Authorization'])
    click.echo("SIMRUN")
    if auth:
        return jsonify(auth)
    else:
        if 'Rounds' in request.form.to_dict().keys():
            run = simserver.run_simulation(request.form.to_dict()['Rounds'])
        else:
            run = simserver.run_simulation(1)
        return jsonify({
            "status": 200,
            "message": run['message'],
            "data": run['data']
        })

@simulations.route('/save', methods=['POST'])
def save():
    click.echo(request)
    try:
        click.echo("Trying First")
        r = request.get_data().decode("utf-8").replace("'", '"')
        click.echo(r)
        r = json.loads(r)
        click.echo(r)
        r = {"Request": r}
    except:
        try:
            click.echo("Trying JSON")
            r = {"Request": request.get_json()}
        except:
            try:
                click.echo("Trying DATA")
                r = request.get_data().decode("utf-8")
            except:
                try:
                    r = request.base_url
                except:
                    r = "Not sure"
                    return(jsonify(r))
    try:
        click.echo(type(r))
        click.echo(r)
    except:

        click.echo(r)
    return jsonify(r)
