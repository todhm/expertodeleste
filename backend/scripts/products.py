import json
import logging
import traceback

import click
from pymongo import MongoClient
from flask.cli import AppGroup
from mongoengine import get_db

from dataparser.tags import change_tag_name_list, add_additional_tag_to_product
from models.product_data import ProductData
from shopify_dao.product import ProductDao
from shopify_dao.shop_app import create_shopify_app
from config import ProductionConfig
from crawler.hayneedle import parse_needle_data
from crawler.furniturepick import parse_furniturepick_data
from crawler.furniturecart import parse_furniturecart_data
from crawler.driver_utils import create_profile_driver


logger = logging.getLogger(__name__)


product_cli = AppGroup('product')


@product_cli.command('description')
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
    for product_data in product_data_list:
        try:
            product_dao.upsert_product(product_data, selected_keys=["descriptionHtml"])
            logger.info(f"Success {product_data.productId}")
        except Exception:
            logger.error(f"Error while change description {product_data.productId} {traceback.format_exc()}")


@product_cli.command('tags')
@click.argument('productid', required=False)
def tag_fix_script(productid):
    db = get_db()
    shop = create_shopify_app()
    product_dao = ProductDao(shop, db)
    if productid:
        productid = productid.strip()
        product_data_list = product_dao.fetch_all_products({"productId": productid})
    else:
        product_data_list = product_dao.fetch_all_products({"brandName": "Anderson Teak"})
    for product_data in product_data_list:
        try:
            add_additional_tag_to_product(product_data)
            product_dao.upsert_product(product_data, selected_keys=["tags"], update_mongo=True, update_meta=False)
            logger.info(f"Success {product_data.productId}")
        except Exception:
            logger.error(f"Error while change description {product_data.productId} {traceback.format_exc()}")



@product_cli.command('crawl')
@click.argument('productid', required=False)
def crawl_product(productid):
    db = get_db()
    shop = create_shopify_app()
    product_dao = ProductDao(shop, db)
    driver = create_profile_driver()
    if productid:
        productid = productid.strip()
        product_data_list = product_dao.fetch_all_products({"productId": productid})
    else:
        product_data_list = product_dao.fetch_all_products()

    for product_data in product_data_list:
        if 'hayneedle' in product_data.goodsUrl:
            product_data = parse_needle_data(driver, product_data.goodsUrl)
        elif 'furniturepick' in product_data.goodsUrl:
            product_data = parse_furniturepick_data(driver, product_data.goodsUrl)
        elif 'furniturecart' in product_data.goodsUrl:
            product_data = parse_furniturecart_data(driver, product_data.goodsUrl)
        product_dao.upsert_product(
            product_data, 
            selected_keys=["variants"],
            update_meta=True,
            update_mongo=True,
            selected_mongo_fields=["skuList", "additionalProductList", "defaultSetList", "reviewList"]
        )


@product_cli.command('product')
@click.argument('productid', required=False)
def crawl_product(productid):
    db = get_db()
    shop = create_shopify_app()
    product_dao = ProductDao(shop, db)
    if productid:
        productid = productid.strip()
        product_data_list = product_dao.fetch_all_products({"productId": productid})
    else:
        product_data_list = product_dao.fetch_all_products()

    for product_data in product_data_list:
        product_dao.upsert_product(product_data)


@product_cli.command('shopify')
@click.argument('productid', required=True)
def fetch_shopify_data(productid):
    db = get_db()
    shop = create_shopify_app()
    product_dao = ProductDao(shop, db)
    product_data = product_dao.fetch_product_data_from_shopify(productid)
    product_dao.mongo_dao.upsert_mongo_product_data(product_data)

def create_all_products():
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        shop = create_shopify_app()
        db = client[ProductionConfig.DB_NAME]
        product_dao = ProductDao(shop, db)
        with open('datacollections/productdata.json') as f:
            product_data_list = json.load(f)
            for product_data in product_data_list:
                product_data = ProductData(**product_data)
                try:
                    product_data.productType = "Kitchen & Dining Furniture Sets"
                    if not db.product.find_one({'productId': product_data.productId}):
                        db.product.insert_one(product_data.to_json)
                    product_data = product_dao.fetch_product(product_data.productId)
                except Exception as e:
                    logger.error(f"Error while matching data {str(e)} {product_data.productId}" + traceback.format_exc())
                try:
                    product_data = product_dao.upsert_product(product_data)
                    logger.info(f"Success {product_data.shopifyId}")
                except Exception as e:
                    logger.error(f"Error while call update api {str(e)} {product_data.productId}" + traceback.format_exc())



def update_product_tags():
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        shop = create_shopify_app()
        db = client[ProductionConfig.DB_NAME]
        product_dao = ProductDao(shop, db)
        product_data_list = product_dao.fetch_all_products()
        for _, product in enumerate(product_data_list):
            product_data = product_dao.fetch_product(product.productId)
            product_data.tagList = list(map(change_tag_name_list, product_data.tagList))
            try:
                product_data = product_dao.upsert_product(product_data, selected_keys=["tags"])
                print(f"Success {product_data.shopifyId}")
            except Exception as e:
                logger.error(f"Error while call update api {str(e)} {product_data.productId}" + traceback.format_exc())
