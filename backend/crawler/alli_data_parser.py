
import re
from typing import Dict, List, Tuple
from datetime import datetime as dt

from bs4 import BeautifulSoup
import requests
import demjson
from bs4.element import Tag

from models.product_data import Sku, OptionData, ReviewData, WarehouseData
from dataparser.dictdata import undefined_to_none


def parse_option_name_list(apidata: Dict) -> List[str]:
    product_option_list = apidata['skuInfo'].get('propertyList', [])
    option_name_list = []
    for option in product_option_list:
        option_name = option['skuPropertyName']
        if option_name not in option_name_list:
            option_name_list.append(option_name)
    return option_name_list


def create_property_map(apidata: Dict) -> Dict:
    property_map = {}
    for property_data in apidata['skuInfo']["propertyList"]:
        for data in property_data['skuPropertyValues']:
            property_map[f"{property_data['skuPropertyId']}:{data['propertyValueId']}"] = data
    return property_map


def parse_none_option_price(apidata: Dict) -> Tuple[int, int]:
    for sku_dict in apidata['skuInfo']["skuList"]:
        if sku_dict.get('skuActivityPriceVO'):
            inner_sku_dict = sku_dict['skuActivityPriceVO']
            stock_count = inner_sku_dict.get("skuActivityStock") if inner_sku_dict.get("skuActivityStock") else sku_dict["skuStock"]
            return inner_sku_dict["skuActivityAmount"]["value"], stock_count
        else:
            inner_sku_dict = sku_dict['skuAmount']
            return inner_sku_dict["value"], sku_dict["skuStock"]


def parse_sku_list(apidata: Dict, promotion_price: float = 0.0, option_name_list: List[str] = []) -> List[Sku]:
    sku_list: List[Sku] = []
    property_map = create_property_map(apidata)
    for sku_dict in apidata['skuInfo']["skuList"]:
        if sku_dict.get('skuActivityPriceVO'):
            inner_sku_dict = sku_dict['skuActivityPriceVO']
            stock_count = inner_sku_dict.get("skuActivityStock") if inner_sku_dict.get("skuActivityStock") else sku_dict["skuStock"]
            sku = Sku(
                skuId=str(sku_dict["skuId"]),
                suuplierSku=str(sku_dict["skuId"]),
                isSoldOut=stock_count == 0,
            )
            price = inner_sku_dict["skuActivityAmount"]["value"]
        else:
            inner_sku_dict = sku_dict['skuAmount']
            stock_count = sku_dict["skuStock"]
            sku = Sku(
                skuId=str(sku_dict["skuId"]),
                supplierSku=str(sku_dict["skuId"]),
                isSoldOut=sku_dict["skuStock"] == 0,
            )
            price = inner_sku_dict["value"]
        sku.warehouseInfo = [WarehouseData(stock=stock_count)]
        before_sales_price_list = [
            'skuAmount',
            'skuBulkAmount'
        ]
        before_sale_price = price
        for key  in  before_sales_price_list:
            if sku_dict.get(key):
                before_sale_price = sku_dict[key]['value']
                break
        sku.cost = price + promotion_price
        sku.beforeSalePrice = before_sale_price + promotion_price
        sku_attr = sku_dict["skuAttr"]
        option_list = sku_attr.split(';')
        option_data_list = []
        option_made = True
        for opt_idx, option_string in enumerate(option_list):
            option_name = option_name_list[opt_idx]
            option_key_list = option_string.split("#")
            option_key = option_key_list[0]
            try:
                option_dict_data = property_map[option_key]
            except Exception:
                option_made = False
                break
            option_data = OptionData(
                optionImage=option_dict_data.get('skuPropertyImagePath'),
                optionValue=option_dict_data['propertyValueDisplayName'],
                optionName=option_name
            )
            option_data_list.append(option_data)
        if not option_made:
            continue
        sku.optionList = option_data_list
        sku_list.append(sku)
    return sku_list


def return_mobile_goods_description(apidata) -> str:
    html_url = apidata['descInfo']['productDescUrl']
    body_tag = BeautifulSoup(requests.get(html_url).text, 'html.parser')
    return str(body_tag)


# Mobile 페이지를 방문한 driver가 필요함
def return_pc_json_data(driver, pcurl: str) -> Dict:
    headers = {
        'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Referer': pcurl,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'
    }
    driver_cookies = driver.get_cookies()
    cookies = {c['name']: c['value'] for c in driver_cookies}
    pcdata = requests.get(
        pcurl,
        cookies=cookies, headers=headers
    ).text
    pattern = re.compile(r"window.runParams = ({.*?}?});.*var GaData", re.MULTILINE | re.DOTALL)
    data_json: Dict = demjson.decode(re.search(pattern, pcdata).group(1), return_errors=True).object
    return undefined_to_none(data_json)['data']


def make_review_url(alli_id: str, apidata: Dict) -> str:
    owner_member_id = apidata['sellerInfo']['sellerAdminSeq']
    company_id = apidata['sellerInfo']['companyId']
    url = (
        f"https://feedback.aliexpress.com/display/productEvaluation.htm?v=2&productId={alli_id}"
        f"&ownerMemberId={owner_member_id}&companyId={company_id}&memberType=seller&startValidDate=&i18n=true"
    )
    return url

def parse_single_review_tab(feedback_div: Tag) -> ReviewData:
    feedback = feedback_div.find("dt", {'class': "buyer-feedback"})
    feedback_text = feedback.findAll('span')[0].text
    review_time = feedback.findAll('span')[1].text
    review_time = dt.strptime(review_time, "%d %b %Y %H:%M")
    review_time = dt.strftime(review_time, '%Y-%m-%d %H:%M:%S')
    points = re.search(r'(\d+)', feedback_div.find('span', attrs={"class": "star-view"}).find("span").get('style')).group(1)
    points = int(points) / 20
    img_list = [x.get("data-src") for x in feedback_div.findAll("li", attrs={"class": "pic-view-item"})]
    return ReviewData(
        reviewTitle=feedback_text,
        reviewText=feedback_text,
        reviewPoint=points,
        reviewTime=review_time,
        reviewImageList=img_list,
    )


def parse_reviewer_tab(review_data: ReviewData, review_div: Tag) -> ReviewData:
    reviewer = review_div.find("span", attrs={"class": "user-name"}).text.strip()
    review_data.writer = reviewer
    return review_data


def parse_review_page(review_string: str) -> List[ReviewData]:
    soup = BeautifulSoup(review_string, "html.parser")
    review_list = []
    feedback_div_list = soup.findAll('div', attrs={"class": "fb-main"})
    reviwer_div_list = soup.findAll('div', attrs={"class": "feedback-item clearfix"})
    for reviewer_div, feedback_div in zip(reviwer_div_list, feedback_div_list):
        try:
            review_data = parse_single_review_tab(feedback_div)
            review_data = parse_reviewer_tab(review_data, reviewer_div)
            review_list.append(review_data)
        except Exception:
            continue
    return review_list
