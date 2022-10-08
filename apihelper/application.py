import os

from flask import Flask
from flask_cors import CORS
from api import api
from api_app.delivery import ns as delivery




is_admin = os.environ.get("IS_ADMIN", 'False')


def create_app(config_object='config.DevelopmentConfig', **config_overrides):

    # instantiate the app

    app = Flask("smoothdining api app")
    app.config.from_object(config_object)
    app.config.update(config_overrides)
    api.add_namespace(delivery)
    api.init_app(app)
    CORS(app)
    return app
