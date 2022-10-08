import json
import logging
import traceback

from pymongo import MongoClient

from shopify_dao.excel.reviews import judgeme_review_excel
from config import ProductionConfig


logger = logging.getLogger(__name__)


def create_judge_excel():
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        try:
            judgeme_review_excel(db)
            logger.info(f"Success create reviews")
        except Exception as e:
            logger.error(f"Error while call update api " + traceback.format_exc())


def create_specific_reviews():
    fname = input("getfname")
    with open(f"datacollections/{fname}.json") as f:
        link_map = json.load(f)
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        try:
            goods_url_list = []
            for key in link_map:
                goods_url_list.extend(link_map[key])
            additional_query = {
                "goodsUrl": {
                    "$in": goods_url_list
                }
            }
            judgeme_review_excel(db, additional_query=additional_query)
            logger.info(f"Success create reviews")
        except Exception as e:
            logger.error(f"Error while call update api " + traceback.format_exc())
