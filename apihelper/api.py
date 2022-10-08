import os

from flask_restx import Api
from flask_cors import cross_origin

is_debug = '/' if os.getenv('FLASK_ENV') == 'development' else False
api = Api(doc=is_debug, decorators=[cross_origin(send_wildcard=True)])
