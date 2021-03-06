from flask import jsonify, Blueprint, request
from apiserver.blueprints.users.views import odbserver as OAuth
from apiserver.blueprints.simulations.models import Pole
import click

simulations = Blueprint('simulations', __name__)
simserver = Pole()
try:
    simserver.open_db()
except:
    pass


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
            "data": simserver.quality_check(family['data'])
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

        run['data']['graph'] = simserver.quality_check(run['data']['graph'])
        return jsonify({
            "status": 200,
            "message": run['message'],
            "data": run['data']
        })

@simulations.route('/simulations/rung_et', methods=['GET'])
def run_get():

    if 'Rounds' in request.form.to_dict().keys():
        run = simserver.run_simulation(request.form.to_dict()['Rounds'])
    else:
        run = simserver.run_simulation(10)

    run['data']['graph'] = simserver.quality_check(run['data']['graph'])
    return jsonify({
        "status": 200,
        "message": run['message'],
        "data": run['data']
    })


@simulations.route('/simulations/get_risks', methods=['GET'])
def get_risks():

    r = simserver.get_risks()
    return jsonify(r)

