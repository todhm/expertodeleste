from typing import Dict, List
import logging
import re
import json
import traceback

from bs4 import BeautifulSoup
import requests

from models.product_data import ProductData
from dataparser.dictdata import find_keys_from_dict


logger = logging.getLogger(__name__)


def parse_title(naver_basic_json: Dict) -> str:
    return naver_basic_json['product']['A']['name']


def parse_description(link: str) -> str:
    return json.loads(requests.get(link).text)['renderContent']


def parse_desc_url(naver_basic_json: Dict) -> str:    
    return f"https://shopping.naver.com/v1/products/{naver_basic_json['product']['A']['id']}/contents/{naver_basic_json['product']['A']['productNo']}/PC"


def parse_option_name_list(naver_basic_json: Dict) -> List[str]:
    for result in find_keys_from_dict(naver_basic_json, 'combinationOptions'):
        if type(result) is list and len(result) > 0:
            return [r['groupName'] for r in result]
    for result in find_keys_from_dict(naver_basic_json, 'simpleOptions'):
        if type(result) is list and len(result) > 0:
            return [r['groupName'] for r in result]
    for result in find_keys_from_dict(naver_basic_json, 'standardOptions'):
        if type(result) is list and len(result) > 0:
            return [r['groupName'] for r in result]
    return []


def parse_main_image_list(naver_basic_json: Dict) -> List[str]:    
    for result in find_keys_from_dict(naver_basic_json, 'productImages'):
        if type(result) is list:
            return [r['url'] for r in result]
    raise ValueError("Cannot find main image list")


def parse_naver_basic_price(naver_basic_json: Dict) -> int:
    for result in find_keys_from_dict(naver_basic_json['product'], 'discountedSalePrice'):
        if type(result) is int:
            return result
    raise ValueError("Cannot find  price")


def return_naver_json(link: str) -> Dict:
    response = requests.get(link)
    soup = BeautifulSoup(response.text, 'html.parser')
    data_script_tag = soup.findAll('script', text=re.compile('window.__PRELOADED_STATE__='))
    return json.loads(
        re.search(
            'window.__PRELOADED_STATE__\=({.*})',
            str(data_script_tag[0])
        ).group(1)
    )


def crawl_product(link: str) -> ProductData:
    try:
        naver_basic_json = return_naver_json(link)
    except Exception:
        raise ValueError("Error while return basic json")

    try:
        product_data = ProductData(
            goodsUrl=link,
        )
    except Exception:
        pass
    try:
        product_data.goodsName = parse_title(naver_basic_json)
    except Exception:
        raise ValueError("Error while making title")
    
    try:
        product_data.mainImageList = parse_main_image_list(naver_basic_json)
    except Exception:
        raise ValueError("Error while making main image lists")

    try:
        shipping_price = naver_basic_json['product']['A']['productDeliveryInfo']['baseFee']
        original_price = parse_naver_basic_price(naver_basic_json)
        product_data.cost = original_price + shipping_price
    except Exception:
        raise ValueError("Error while parse price price")

    try:
        desc_url = parse_desc_url(naver_basic_json)
        product_data.description = parse_description(desc_url)
    except Exception:
        raise ValueError(f"Error while parsing description image list {traceback.format_exc()}")

    return product_data
