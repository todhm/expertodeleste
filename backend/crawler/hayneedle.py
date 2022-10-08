import logging
from typing import Dict, List
import re
from datetime import datetime as dt
import traceback

import requests
import demjson
from selenium import webdriver  # Import from seleniumwire

from models import product_data
from dataparser.tags import add_additional_tag_to_product


logger = logging.getLogger(__name__)


def return_base_json(driver: webdriver.Chrome) -> Dict:
    pattern = re.compile(r"window.__PRELOADED_STATE__ = ({.*?});", re.MULTILINE | re.DOTALL)
    result = re.search(pattern, driver.page_source)
    data_json = demjson.decode(result.group(1))
    return data_json


def parse_option_cases(data_json: Dict, pd: product_data.ProductData) -> None:
    options = data_json['pageData']['product']['options']
    option_list = data_json['pageData']['product']['variations']
    sku_list = []
    option_name_list = []
    for sku_idx, sku_data in enumerate(option_list):
        sku = product_data.Sku(skuId=sku_data['variationID'], supplierSku=sku_data['supplierSku'])
        sku.beforeSalePrice = float(sku_data['listPrice'])
        sku.price = float(sku_data['ourPrice'])
        option_selection_list = []
        for option_data_idx, option_val in enumerate(sku_data['optionValues']):        
            if len(options) > option_data_idx:
                match_option_data_list = options[option_data_idx]['values']
            else:
                match_option_data_list = []
            od = product_data.OptionData(optionValue=option_val['value'], optionName=option_val['name'])
            if sku_idx == 0:
                option_name_list.append(od.optionName)
            for match_option in match_option_data_list:
                if match_option['text'] == od.optionValue:
                    od.optionId = match_option['optionValueID']
                    if match_option['optionImg']:
                        od.optionImage = "https:" + match_option['optionImg']
            option_selection_list.append(od)
        sku.optionList = option_selection_list
        warehouse_data_source_list = sku_data['afsQuantity']
        warehouse_data_list = []
        any_stock_left = False
        for warehouse_info in warehouse_data_source_list:
            wd = product_data.WarehouseData(
                stock=warehouse_info['quantity'],
                warehouseId=warehouse_info['warehouseCode'],
                warehouseName=warehouse_info['warehouseCode']
            )
            warehouse_data_list.append(wd)
            if wd.stock > 0:
                any_stock_left = True
        sku.warehouseInfo = warehouse_data_list
        sku.isSoldOut = sku_data['status'] != "IN_STOCK" or (sku.warehouseInfo  and any_stock_left is False)
        sku_list.append(sku)
    pd.skuList = sku_list
    pd.optionNameList = option_name_list

    
def parse_brand_data(data_json) -> product_data.BrandData:
    brandData = product_data.BrandData(brandName=data_json['pageData']['product']['brand'])
    for data in data_json['pageData']['facetValues']:
        if data.get('media'):
            media = data['media']
            brandData.brandLogo = f"https://content.haycdn.com/mgen/brandLogo.ms?logo=dynamic_library/vendor_logos/{media}"
        if data.get('longDescription'):
            brandData.brandDescription = data['longDescription']
        if data.get('facetID'):
            brandData.brandId = data.get('facetID')
    return brandData
        

def parse_delivery_data_json(pid: str) -> List[product_data.DeliveryData]:
    url = f'https://www.hayneedle.com/sf-service/shippingCalculations/getShippingCalculations?country=US&includes=all&parentSku={pid}&state=NY&zipcode=10007'
    result = requests.get(url).json()
    delivery_data_list = []
    for delivery_source_data in result['shippingCalculationResponses']:

        dd = product_data.DeliveryData(
            deliveryName=delivery_source_data['name'],
            deliveryDescription=delivery_source_data['shortDescription'],
            price=delivery_source_data['methodCost'],
        )
        try:
            origin_date = dt.strptime(delivery_source_data['shipDate'], '%Y-%m-%dT%H:%M:%S-0600')
        except Exception:
            origin_date = dt.strptime(delivery_source_data['shipDate'], '%Y-%m-%dT%H:%M:%S-0500')

        try:
            min_date = dt.strptime(delivery_source_data['deliveryDateLow'], '%Y-%m-%dT%H:%M:%S-0600')
        except Exception:
            min_date = dt.strptime(delivery_source_data['deliveryDateLow'], '%Y-%m-%dT%H:%M:%S-0500')
        try:
            max_date = dt.strptime(delivery_source_data['deliveryDateHigh'], '%Y-%m-%dT%H:%M:%S-0600')
        except Exception:
            max_date = dt.strptime(delivery_source_data['deliveryDateHigh'], '%Y-%m-%dT%H:%M:%S-0500')
        max_days_delta = max_date - origin_date
        min_days_delta = min_date - origin_date
        dd.minDays = min_days_delta.days
        dd.maxDays = max_days_delta.days
        delivery_data_list.append(dd)
    return delivery_data_list


def parse_review_response_list(response: Dict) -> List[product_data.ReviewData]:
    review_data_list = []
    for review_source_data in response['results'][0]['reviews']:
        datetimeobj = dt.fromtimestamp(review_source_data['details']['created_date']/1000)
        reviewtime = dt.strftime(datetimeobj, "%Y-%m-%d %H:%M:%S")
        review_image_list = ['https:' + x['uri'] for x in review_source_data['media']]
        rd = product_data.ReviewData(
            writer=review_source_data['details']['nickname'],
            reviewText=review_source_data['details']['comments'],
            reviewTitle=review_source_data['details']['headline'],
            reviewPoint=review_source_data['metrics']['rating'],
            reviewTime=reviewtime,
            reviewImageList=review_image_list
        )
        review_data_list.append(rd)
    return review_data_list


def return_review_list_from_data(data_json: Dict, driver: webdriver.Chrome) -> List[product_data.ReviewData]:
    driver_cookies = driver.get_cookies()
    cookies = {c['name']: c['value'] for c in driver_cookies}
    api_key = data_json['siteSettings']['pwr_api_key']
    pid = data_json['page']['id']
    first_page_response = requests.get(
        f'https://display.powerreviews.com/m/9890/l/en_US/product/{pid}/reviews?apikey={api_key}&_noconfig=true', 
        cookies=cookies
    ).json()
    review_data_list = parse_review_response_list(first_page_response)
    for i in range(10, first_page_response['paging']['total_results'], 10):
        try:
            url = f'https://display.powerreviews.com/m/9890/l/en_US/product/{pid}/reviews?paging.from={i}&paging.size=10&filters=&search=&sort=Newest&image_only=false&_noconfig=true&apikey={api_key}'
            response = requests.get(url, cookies=cookies).json()
            review_data_list.extend(parse_review_response_list(response))
        except Exception:
            continue
    return review_data_list

def return_question_list(data_json: Dict) -> List[product_data.QuestionData]:
    question_data_list = []
    for question_source_data in data_json['pageData']['productQuestions']['questions']:
        if question_source_data['answers']:
            time_str = question_source_data['createdDate'].replace("-0500", '').replace("-0600", '')
            created_date = dt.strptime(time_str, '%Y-%m-%dT%H:%M:%S')
            created_str = dt.strftime(created_date, "%Y-%m-%d %H:%M:%S")
            qd = product_data.QuestionData(
                questionTitle=question_source_data['questionText'],
                answer=question_source_data['answers'][0]['answerText'],
                questionTime=created_str,
                writer=question_source_data['authorName']
            )
            question_data_list.append(qd)
    return question_data_list


def make_specification_html(product_data: product_data.ProductData) -> str:
    row_strings = ""
    for must_info in product_data.goodsMustInfo:
        value_p_list = ''.join([f"<p>{value}</p>" for value in must_info.valueList])
        row_strings += f"<tr><td>{must_info.key}</td><td>{value_p_list}</td></tr>"
    html_string = f'<table width="100%"><tbody>{row_strings}</tbody></table>'
    return html_string


def make_delivery_html(product_data: product_data.ProductData) -> str:
    header_string: str = '''
        <thead>
          <tr>
            <th scope="col">Delivery Methods</th>
            <th scope="col">Estimated Delivery Time</th>
            <th scope="col">Delivery Price</th>
          </tr>
        </thead>
    '''
    row_strings = ""
    for delivery_info in product_data.deliveryDataList:
        if delivery_info.minDays < delivery_info.maxDays:
            delivery_day_strings = f'{delivery_info.minDays} ~ {delivery_info.maxDays} Business Days'
        else:
            delivery_day_strings = f'{delivery_info.minDays} Business Days'
            
        row_strings += f"<tr><td>{delivery_info.deliveryName}</td><td>{delivery_day_strings}</td><td>{delivery_info.price} USD</td></tr>"
    html_string = f'<table width="100%">{header_string}<tbody>{row_strings}</tbody></table>'
    return html_string

def make_shopify_description(product_data: product_data.ProductData) -> str:
    header_html = '''
    <ul class="tabs">
        <li><a class="active" href="#tab1">Description</a></li>
        <li><a href="#tab2">Specs</a></li>
        <li><a href="#tab3">Brand</a></li>
        <li><a href="#tab4">Shipping</a></li>
    </ul>'''
    description_part = f'''
    <li class="active" id="tab1">
        {product_data.description}
    </li>
    '''
    specification_part = f'''
        <li class="active" id="tab2">
        {make_specification_html(product_data)}
        </li>
    '''
    brand_part = f'''
        <li class="active" id="tab3">
            <div class="spr-container">
                <div class="spr-header">
                    <img src="{product_data.brandData.brandLogo}">
                </div>
                <div class="spr-content">{product_data.brandData.brandDescription}</div>
            </div>
        </li>
    '''
    delivery_part = f'''
    <li class="active" id="tab4">
        {make_delivery_html(product_data)}
    </li>
    '''
    content_html = f'''
    <ul class="tabs-content">
        {description_part}
        {specification_part}
        {brand_part}
        {delivery_part}
    </ul>'''
    return header_html + content_html


def parse_needle_data(driver: webdriver.Chrome, url: str) -> product_data.ProductData:
    try:
        pd = product_data.ProductData(goodsUrl=url)
        driver.get(url)
        data_json = return_base_json(driver)
    except Exception:
        message = f"Error while fetching default json data {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)

    try:
        image = data_json['pageData']['product']['images']
        pd.mainImageList = ['https:' + x['url'] for x in image['images']]
        pd.goodsName = data_json['pageData']['product']['name']
        pd.included = data_json['pageData']['product']['included']
        pd.description = data_json['pageData']['product']['description']
        pd.brandName = data_json['pageData']['product']['brand']
        pd.productId = data_json['page']['id']
    except Exception:
        message = f"Error while parsing basic product data {url}"
        logger.error(message)
        raise ValueError(message)
    
    try:
        video_url_list = []
        for x in data_json['pageData']['product'].get('media', []):
            if x.get('type') == "YOUTUBE_VIDEO":
                video_url_list.append(f"https:{x.get('url')}")
        pd.videoUrlList = video_url_list
    except Exception:
        message = f"Error while parsing video urls {url}"
        logger.error(message)
    
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
        pd.reviewList = return_review_list_from_data(data_json, driver)
    except Exception as e:
        message = f"Error while parsing review info {url} {str(e)}"
        logger.error(message)
        pass
    try:
        pd.questionList = return_question_list(data_json)
    except Exception as e:
        message = f"Error while parsing question info {url} {str(e)}"
        logger.error(message)
        pass
    try:
        add_additional_tag_to_product(pd)
    except Exception:
        pass
    return pd

