import logging
from typing import Dict, List
import re
import json
from datetime import datetime as dt

import requests
import demjson
from selenium import webdriver  # Import from seleniumwire

from models import product_data
from dataparser.tags import add_additional_tag_to_product


logger = logging.getLogger(__name__)



def return_base_json(driver: webdriver.Chrome) -> Dict:
    pattern = re.compile(r"window.__INITIAL_STATE__ = ({.*?});", re.MULTILINE | re.DOTALL)
    result = re.search(pattern, driver.page_source)
    data_json = demjson.decode(result.group(1))
    inner_json = json.loads(data_json['_PDP_BOOTSTRAP_DATA'])
    return inner_json


def parse_macsys_data(driver: webdriver.Chrome, url: str) -> product_data.ProductData:
    try:
        pd = product_data.ProductData(goodsUrl=url)
        driver.get(url)
        data_json = return_base_json(driver)
    except Exception:
        message = f"Error while fetching default json data {url}"
        logger.error(message)
        raise ValueError(message)

        
    try:
        pd.mainImageList = [
            f"https://slimages.macysassets.com/is/image/MCY/products/{x['filePath']}" 
            for x in data_json['product']['imagery']['images'] if not x.get('video')
        ]
        pd.goodsName = data_json['product']['detail']['name']
        pd.included = data_json['pageData']['product']['included']
        pd.description = data_json['pageData']['product']['description']
        pd.brandName = data_json['pageData']['product']['brand']
        pd.videoUrlList = data_json['pageData']['product']['videos']
        pd.productId = data_json['page']['id']
    except Exception:
        message = f"Error while parsing basic product data {url}"
        logger.error(message)
        raise ValueError(message)
        
    
    try:
        mi_list = []
        for i in data_json['pageData']['product']['attributeValues']:
            mi = product_data.MustInfo(key = i['name'])
            mi.valueList = [x['value'] for x in i['values']]
            mi_list.append(mi)
        pd.goodsMustInfo = mi_list
    except Exception:
        message = f"Error while parsing must info {url}"
        logger.error(message)
        raise ValueError(message)
    
    try:
        parse_option_cases(data_json, pd)
    except Exception:
        message = f"Error while parsing option info {url}"
        logger.error(message)
        raise ValueError(message)

    try:
        pd.deliveryDataList =  parse_delivery_data_json(pd.productId)
    except Exception:
        message = f"Error while parsing delivery info {url}"
        logger.error(message)
        raise ValueError(message)

    try:
        pd.brandData = parse_brand_data(data_json)
    except Exception:
        message = f"Error while parsing brand info {url}"
        logger.error(message)
        raise ValueError(message)
        
    try:
        pd.reviewList = return_review_list_from_data(data_json)
    except Exception:
        message = f"Error while parsing review info {url}"
        logger.error(message)
        raise ValueError(message)
    try:
        pd.questionList = return_question_list(data_json)
    except Exception:
        message = f"Error while parsing review info {url}"
        logger.error(message)
        raise ValueError(message)
    try:
        add_additional_tag_to_product(pd)
    except Exception:
        pass
    return pd

