import traceback
import logging
import json
from typing import Optional, Dict, List
import asyncio

from pymongo import MongoClient
from flask.cli import AppGroup
from selenium import webdriver

from crawler.hayneedle import parse_needle_data
from crawler.furniturepick import parse_furniturepick_data
from crawler.furniturecart import parse_furniturecart_data
from crawler.alli import AlliCrawlHandler
from commissions.alli import convert_alli_commissions
from crawler.driver_utils import create_profile_driver
from config import ProductionConfig
from shopify_dao.product import ProductDao
from shopify_dao.shop_app import create_shopify_app
from models.mongo_models.product_data import BrandDataCollection, AdditionalProductList
from dataparser.htmlparser import make_inline_style
from scripts.naver import naver_smartstore_script

logger = logging.getLogger(__name__)


crawl_cli = AppGroup('crawl')


def crawl_product_data(
    driver: webdriver.Chrome,
    data_map: Dict, 
    link: str,
    additional_product: Optional[AdditionalProductList] = None,
    tag_list: List[str] = [],
):
    try:
        if 'hayneedle' in link:
            product_data = parse_needle_data(driver, link)
        elif 'furniturepick' in link:
            product_data = parse_furniturepick_data(driver, link, additional_product)
        elif 'furniturecart' in link:
            product_data = parse_furniturecart_data(driver, link, additional_product)
        product_data.productType = "Kitchen & Dining Furniture Sets"
        for tag in tag_list:
            product_data.add_tag(tag)
        brand_data = product_data.brandData
        if brand_data and brand_data.brandName and data_map.get(brand_data.brandName):
            real_brand_data = data_map[brand_data.brandName]
            product_data.brandData.brandDescription = make_inline_style(real_brand_data.brandDescription)
            product_data.brandData.brandLogo = real_brand_data.brandLogo
        return product_data
    except Exception:
        message = f"Error while parse {link} {traceback.format_exc()}"
        logger.error(f"Error while parse {link} {traceback.format_exc()}")
        raise ValueError(message)
                

@crawl_cli.command('links')
def crawl_links():
    fname = input('check your fname')
    with open(f"datacollections/{fname}.json") as f:
        link_map = json.load(f)
    driver = create_profile_driver()
    data_map = {}
    for brand_data in BrandDataCollection.objects.all():
        data_map[brand_data.brandName] = brand_data
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        product_dao = ProductDao(shop, db)
        for tag in link_map:
            new_tag_list = [x.strip() for x in tag.split(',') if x]
            tag_list = ["Dining Sets"]
            tag_list.extend(new_tag_list)
            link_list = link_map[tag]
            for link in link_list:
                try:
                    product_data = crawl_product_data(driver, data_map, link, tag_list=tag_list)
                except Exception:
                    logger.error(f"Error whlie crawl data {link} {traceback.format_exc()}")
                try:
                    product_data = product_dao.upsert_product(product_data)
                    print(product_data.shopifyId)
                except Exception:
                    logger.error(f"Error upsert shopify data {link} {traceback.format_exc()}")
                
                for additional_product in product_data.additionalProductList:
                    try:
                        new_product_data = crawl_product_data(
                            driver, 
                            data_map, 
                            additional_product.goodsUrl, 
                            additional_product=additional_product, 
                            tag_list=["Additional Product"]
                        )
                        new_product_data = product_dao.upsert_product(new_product_data)
                        new_product_data = product_dao.upsert_mongo_db(new_product_data)
                        variant_id = product_dao.fetch_first_variant_id(new_product_data.productId)
                        additional_product.shopifyVariantId = variant_id
                        print("Additional", new_product_data.shopifyId)
                    except Exception:
                        logger.error(f"Error while making additoinal data {additional_product.goodsUrl} {traceback.format_exc()}")
                        continue    
                product_dao.update_metafields(product_data, key_list=['additionalproductlist'])
                print("Additional Product Data Variant Updated")
                

@crawl_cli.command('makejson')
def crawl_links():
    link = input('give me a link')
    driver = create_profile_driver()
    data_map = {}
    for brand_data in BrandDataCollection.objects.all():
        data_map[brand_data.brandName] = brand_data
    try:
        product_data = crawl_product_data(driver, data_map, link, tag_list=[])
    except Exception:
        logger.error(f"Error while parse {link} {traceback.format_exc()}")
        pass
    with open(f'datacollections/{product_data.productId}.json', 'w') as f:
        json.dump(product_data.to_json, f, sort_keys=True, indent=4)
            

@crawl_cli.command('navercrawl')
def crawl_naver_products():
    fname = input('check your fname')
    if not fname:
        fname = "crawlnaverdata"
    with open(f"datacollections/{fname}.json") as f:
        link_map = json.load(f)
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        product_dao = ProductDao(shop, db)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for tag_full in link_map:
            tag = tag_full.split(':')
            tag_list = tag[0].split(',')
            brand_name = tag[1] if tag[1:] else ''
            goods_name = tag[2] if tag[2:] else ''
            link_list = link_map[tag_full]
            for link in link_list:
                product_data = loop.run_until_complete(
                    naver_smartstore_script(
                        link,
                        brand_name=brand_name,
                        goods_name=goods_name,
                        tag_list=tag_list,
                    )
                )
                product_dao.upsert_product(product_data)
        loop.close()


@crawl_cli.command('alli')
def crawl_alli_products():
    fname = input('check your fname')
    if not fname:
        fname = "crawlallidata"
    with open(f"datacollections/{fname}.json") as f:
        link_map = json.load(f)
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        product_dao = ProductDao(shop, db)
        driver = create_profile_driver()
        adh = AlliCrawlHandler(driver)
        for tag_full in link_map:
            tag = tag_full.split(':')
            tag_list = tag[0].split(',')
            brand_name = tag[1] if tag[1:] else ''
            goods_name = tag[2] if tag[2:] else ''
            link_list = link_map[tag_full]
            for link in link_list:
                product_data = adh.parse_crawl_data(link)
                product_data = convert_alli_commissions(product_data)
                product_data.tagList = tag_list
                product_data.brandName = brand_name
                if goods_name:
                    product_data.goodsName = goods_name
                product_dao.upsert_product(product_data)
