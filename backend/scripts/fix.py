from curses import wrapper
import logging

from pymongo import MongoClient
from flask.cli import AppGroup
from bs4 import BeautifulSoup

from mongodao.mongo_dao import MongoDao
from shopify_dao.product import ProductDao
from config import ProductionConfig
from shopify_dao.shop_app import create_shopify_app
from dataparser.htmlparser import HtmlParserDao
from dataparser.tags import remove_none_table_tags
from data_types import tag_types, brand_types

logger = logging.getLogger(__name__)

fix_cli = AppGroup('fix')

# Video Url이 안붙은 데이터 수정하기위한 스크립트 
@fix_cli.command('acmedescriptioncase')
def brand_fix_script():
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        mongo_dao = MongoDao(db, 'product')
        product_dao = ProductDao(shop, db)
        data_list = mongo_dao.fetch_product_list_data({"brandName": "Acme Furniture"})
        for data in data_list:
            if data.videoUrlList:
                embed_id = data.videoUrlList[0]
                if not embed_id in data.description:
                    data.description += (
                        '<div class="product-video-wrapper">'
                        f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{embed_id}" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
                        '</div>'
                    )
                    product_dao.upsert_product(
                        data,
                        selected_keys=['descriptionHtml'],
                        selected_mongo_fields=['description'],
                        update_meta=False
                    )
                    print(data.productId, embed_id)


# Iframe으로되어있던 상세페이지를 video 로 변경후 뮤트시키기
@fix_cli.command('mutevideo')
def mute_video():
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        mongo_dao = MongoDao(db, 'product')
        product_dao = ProductDao(shop, db)
        data_list = mongo_dao.fetch_product_list_data({"brandName": "Vifah", 'videoUrlList.0': {"$exists": True}})
        for data in data_list:
            print(data.productId)
            soup = BeautifulSoup(data.description, 'html.parser')
            wrapper_div = soup.find('div', attrs={"class": "product-video-wrapper"})
            if wrapper_div:
                iframe_div = wrapper_div.find("iframe")
                if iframe_div:
                    video_url = iframe_div.get('src')
                    # autoplay="" controls="" height="315" muted="" width="560"
                    iframe_div.extract()
                    video_tag = soup.new_tag('video',attrs={
                        "autoplay": None,
                        "controls": None,
                        "height": "315",
                        "muted": None,
                        "width": "560"
                    })
                    source_tag = soup.new_tag("source", attrs={
                        "src": video_url,
                        "type": "video/mp4" 
                    })
                    video_tag.append(source_tag)
                    wrapper_div.append(video_tag)
                    data.description = str(soup)
                    product_dao.upsert_product(
                        data,
                        selected_keys=['descriptionHtml'],
                        selected_mongo_fields=['description'],
                        update_meta=False
                    )
                    print(data.productId, "success")


@fix_cli.command('fix_feature_list')
def fix_feature_list():
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        mongo_dao = MongoDao(db, 'product')
        data_list = mongo_dao.fetch_product_list_data({'featureList.0': {"$exists": False}, "shopifyId": {"$exists": True}})
        for data in data_list:
            print(data.productId)
            htmlparserdao = HtmlParserDao(data.description)
            feature_list = htmlparserdao.return_matched_string_list('.//ul[@class="description-feature-wrapper"]/li')
            data.featureList = feature_list
            mongo_dao.upsert_mongo_product_data(
                data,
                ["featureList"]
            )

@fix_cli.command('delete_crawl')
def delete_crawl():
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        mongo_dao = MongoDao(db, 'product')
        query = {
            "brandName": {
                "$nin": [
                    "Winsome",
                    "Manhattan Comfort",
                    "Vifah",
                    "Acme Furniture",
                    "Anderson Teak"
                ]
            }
        }
        result_list = mongo_dao.fetch_data(query)
        print(len(result_list), '총 상품 길이는?')
        all_you_gonna_delte = input("삭제하시겠습니까? y/n")
        if all_you_gonna_delte == 'y':
            mongo_dao.delete_many_query(query)


@fix_cli.command('remove_nonetable')
def remove_nonetable():
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        mongo_dao = MongoDao(db, 'product')
        product_dao = ProductDao(shop, db)
        data_list = mongo_dao.fetch_product_list_data(
            {"brandName": brand_types.ART_FURNITURE, "goodsName": {"$regex": "chair", '$options': 'i'}}
        )
        for data in data_list:
            data.add_tag(tag_types.NONE_TABLE)
            remove_none_table_tags(data)
            product_dao.upsert_product(
                data,
                selected_keys=['tags'],
                selected_mongo_fields=['tagList'],
                update_meta=False
            )
            print(data.goodsName, data.productId, "success")


@fix_cli.command('change_shiptype_tag')
def add_shiptype_tag():
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        mongo_dao = MongoDao(db, 'product')
        product_dao = ProductDao(shop, db)
        data_list = mongo_dao.fetch_product_list_data(
            {
                "shopifyId": {"$exists": True}, 
                "brandName": brand_types.WINSOME
            }
        )
        for data in data_list:
            weight_sum = sum([x.packageWeight for x in data.weightInfoList])
            data.remove_tag(tag_types.LTL)
            data.remove_tag(tag_types.PARCEL)
            print('before type', data.tagList, data.shipType)
            if weight_sum >= 100:
                data.shipType = tag_types.LTL
            else:
                data.shipType = tag_types.PARCEL
            data.add_tag(data.shipType)
            print(data.shipType, data.goodsName, data.tagList)
            product_dao.upsert_product(
                data,
                selected_keys=['tags'],
                selected_mongo_fields=['tagList'],
                update_meta=False
            )
            print(data.goodsName, data.productId, "success")
