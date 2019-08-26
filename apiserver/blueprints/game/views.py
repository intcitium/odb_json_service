from flask import Blueprint, jsonify, request
from apiserver.blueprints.game.models import Game
from apiserver.utils import get_request_payload
import click

game = Blueprint('game', __name__)
gameserver = Game()
gameserver.open_db()


@game.route('/game', methods=['GET'])
def index():
    names = gameserver.get_game_names()
    return jsonify({
        "status": 200,
        "message": '''Games Endpoint''',
        "data": names
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


@game.route('/game/setup_game', methods=['GET', 'POST'])
def setup_game():
    try:
        r = get_request_payload(request)
    except Exception as e:
        click.echo(e)

    data = gameserver.setup_game(playerCount=int(r['playerCount']))
    return jsonify({
        "status": 200,
        "message": "Game setup complete with %d players" % (int(r['playerCount'])),
        "gameState": data,
        "ok": True
    })


@game.route('/game/get_game', methods=['GET', 'POST'])
def get_game():
    try:
        r = get_request_payload(request)
    except Exception as e:
        click.echo(e)

    data = gameserver.get_game(gameKey=int(r['gameKey']))
    return jsonify({
        "status": 200,
        "message": "Game %s loading complete" % (data['gameName']),
        "gameState": data,
        "ok": True
    })


@game.route('/game/delete_game', methods=['GET', 'POST'])
def delete_game():
    try:
        r = get_request_payload(request)
    except Exception as e:
        click.echo(e)

    data = gameserver.delete_game(gameKey=int(r['gameKey']))
    return jsonify({
        "status": 200,
        "message": data['message'],
        "gameState": data,
        "ok": True
    })


@game.route('/game/create_move', methods=['GET', 'POST'])
def create_move():
    try:
        r = get_request_payload(request)
    except Exception as e:
        click.echo(e)
    data = gameserver.create_move(
        resourceKeys=r['resourceKeys'],
        targetKeys=r['targetKeys'],
        effectKeys=r['effectKeys'],
        gameKey=r['gameKey'],
        playerKey=r['playerKey']
    )
    return jsonify({
        "status": 200,
        "message": data['result'],
        "gameState": data,
        "ok": True
    })
