import logging

from flask.cli import AppGroup
from mongoengine import get_db

from mongodao.mongo_dao import MongoDao
from intuitive_dao.intuitive_dao import IntuitiveDao

logger = logging.getLogger(__name__)


intuitive_cli = AppGroup('intuitive')


@intuitive_cli.command('intuitive')
def create_intuitive_data():
    db = get_db()
    mongo_dao = MongoDao(db)
    fname = input('check your product fname')
    if not fname:
        fname = 'data.csv'
    fname = f'datacollections/intuitive/{fname}'
    ind = IntuitiveDao(mongo_dao, fname)
    ind.create_new_weight_info()    

    