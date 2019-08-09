from flask import Blueprint, jsonify, request
from apiserver.blueprints.game.models import Game
from apiserver.utils import get_request_payload
import click

game = Blueprint('game', __name__)
gameserver = Game()
gameserver.open_db()


@game.route('/game', methods=['GET'])
def index():
    return jsonify({
        "status": 200,
        "message": '''Games Endpoint
        '''
    })


@game.route('/game/create_player', methods=['GET'])
def create_player():
    r = get_request_payload(request)

    data = gameserver.create_player(name=r['playerName'])
    return jsonify({
        "status": 200,
        "message": "Created player %s with %d resources" % (r['playerName'], len(data['resources'])),
        "player": data
    })

@game.route('/game/setup_game', methods=['GET'])
def setup_game():
    try:
        r = get_request_payload(request)
        click.echo("R %s" % r)
    except Exception as e:
        click.echo(e)
        r = {"playerCount": 3}


    data = gameserver.setup_game(playerCount=int(r['playerCount']))
    return jsonify({
        "status": 200,
        "message": "Game setup complete with %d players" % (int(r['playerCount'])),
        "gameState": data,
        "ok": True
    })
