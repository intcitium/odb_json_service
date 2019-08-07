from flask import Blueprint, jsonify, request
from apiserver.blueprints.game.models import Game
from apiserver.utils import get_request_payload
from flask_cors import CORS

game = Blueprint('game', __name__)
CORS(game)
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
    r = get_request_payload(request)

    data = gameserver.setup_game(playerCount=int(r['playerCount']))
    return jsonify({
        "status": 200,
        "message": "Game setup complete with %d players" % (int(r['playerCount'])),
        "gameState": data
    })
