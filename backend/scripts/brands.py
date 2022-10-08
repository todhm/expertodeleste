import click
import logging

from pymongo import MongoClient
from flask.cli import AppGroup
from mongoengine import get_db

from config import ProductionConfig
from shopify_dao.product import ProductDao
from shopify_dao.shop_app import create_shopify_app
from models.mongo_models.product_data import BrandDataCollection
from dataparser.htmlparser import make_inline_style


logger = logging.getLogger(__name__)

brand_cli = AppGroup('brand')

@brand_cli.command('product')
@click.argument('productid', required=False)
def brand_fix_script(productid):
    db = get_db()
    shop = create_shopify_app()
    product_dao = ProductDao(shop, db)
    if productid:
        productid = productid.strip()
        product_data_list = product_dao.fetch_all_products({"productId": productid})
    else:
        product_data_list = product_dao.fetch_all_products()
    data_map = {}
    for brand_data in BrandDataCollection.objects.all():
        data_map[brand_data.brandName] = brand_data
    for product_data in product_data_list:
        brand_data = product_data.brandData
        if brand_data and brand_data.brandName and data_map.get(brand_data.brandName):
            real_brand_data = data_map[brand_data.brandName]
            product_data.brandData.brandDescription = make_inline_style(real_brand_data.brandDescription)
            product_data.brandData.brandLogo = real_brand_data.brandLogo
            product_dao.update_metafields(product_data)


@brand_cli.command('brandprepare')
def prepare_brand_collections():
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        product_dao = ProductDao(shop, db)
        product_data_list = product_dao.fetch_all_products()
        data_map = {}
        for brand_data in BrandDataCollection.objects.all():
            data_map[brand_data.brandName] = True
        for product_data in product_data_list:
            brand_data = product_data.brandData
            if brand_data and brand_data.brandName and not data_map.get(brand_data.brandName):
                db.brand_data.insert_one(brand_data.to_json)
                data_map[brand_data.brandName] = True
            else:
                if not brand_data or not brand_data.brandName:
                    bdc = BrandDataCollection(
                        brandName=product_data.goodsName,
                    )
                    bdc.save()
                    data_map[product_data.goodsName] = True

            



