import click
import logging

from flask.cli import AppGroup
from mongoengine import get_db

from mongodao.mongo_dao import MongoDao
from google_merchant.google_merchant_dao import GoogleMerchantDao


logger = logging.getLogger(__name__)

google_cli = AppGroup('google')

@google_cli.command('toexcel')
@click.argument('productid', required=False)
def google_merchant_cli(productid):
    db = get_db()
    product_dao = MongoDao(db)
    gmd = GoogleMerchantDao()
    default_query = {
        "shopifyId": {
            "$exists": True,
        },
        "$where": 'this.shopifyId.length > 0'
    }
    if productid:
        productid_list = [x.strip() for x in productid.split(' ')]
        default_query['productId'] = {"$in": productid_list}
    product_data_list = product_dao.fetch_product_list_data(default_query)
    gmd.to_local_excel(product_data_list)
    