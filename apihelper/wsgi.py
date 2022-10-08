import logging

from application import create_app
from dotenv import load_dotenv

load_dotenv('.flask.prod.env')
app = create_app('config.ProductionConfig')


if __name__ == '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
