from flask import jsonify, Blueprint, request
from apiserver.blueprints.game.models import Game
from apiserver.utils import get_request_payload

game = Blueprint('game', __name__)
gameserver = Game()
try:
    gameserver.open_db()
except:
    pass


