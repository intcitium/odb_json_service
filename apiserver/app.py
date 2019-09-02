from flask import Flask
from apiserver.blueprints.home import home
from apiserver.blueprints.users import users
from apiserver.blueprints.chatbot import chatbot
from apiserver.blueprints.simulations import simulations
from apiserver.blueprints.situations import situations
from apiserver.blueprints.osint import osint
from apiserver.blueprints.game import game
from flask_cors import CORS


def create_app():
    app = Flask(__name__)
    app.register_blueprint(home)
    app.register_blueprint(users)
    app.register_blueprint(chatbot)
    app.register_blueprint(simulations)
    app.register_blueprint(situations)
    app.register_blueprint(osint)
    app.register_blueprint(game)
    CORS(app)

    return app

