import logging
import traceback
from typing import List

from selenium import webdriver  # Import from seleniumwire
import lxml.html as LH
from lxml.html import HtmlElement

from models import product_data


logger = logging.getLogger(__name__)



def parse_acme_data(driver: webdriver.Chrome, url: str) -> product_data.ProductData:
    try:
        pd = product_data.ProductData(goodsUrl=url)
        driver.get(url)
    except Exception:
        message = f"Error while fetching requests data {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)
    try:
        root = LH.fromstring(driver.page_source)
        pd.mainImageList = parse_main_image_list(root)
    except Exception:
        message = f"Error while parsing image crawl data {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)
    
    
    try:
        pd.goodsMustInfo = parse_must_info(root)
    except Exception:
        message = f"Error while parsing must info {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)    

    try:
        pd.mainImageList = parse_main_image_list(root)
    except Exception:
        message = f"Error while parsing image crawl data {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)

    try:
        pd.shortDescription = parse_short_description(root)
    except Exception:
        message = f"Error while parsing descriptioin crawl data {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)

    
    try:
        pd.goodsName = parse_title(root)
    except Exception:
        message = f"Error while parsing descriptioin crawl data {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)
    try:
        pd.additionalProductList = parse_additional_data_list(root)
    except Exception:
        message = f"Error while parsing descriptioin crawl data {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)
    return pd


def parse_main_image_list(root: HtmlElement) -> List[str]:
    main_image_list = root.xpath('//div[contains(@class, "fotorama__stage__frame")]/img')
    main_image = main_image_list[0].get('src')
    image_prefix = '/'.join(main_image.split('/')[:-1])
    image_list = []
    for img in root.xpath('//div[contains(@class, "fotorama__thumb")]/img[contains(@class, "fotorama__img")]'):
        image_list.append(image_prefix + '/' + img.get('src').split('/')[-1])
    if not image_list:
        image_list = [main_image]
    return image_list

def parse_must_info(root: HtmlElement) -> List[product_data.MustInfo]:
    data_list = []
    spec_list = root.xpath("//div[@class='product-dimensions']/div[@class='col-lg-6']/ul/li")
    for spec in spec_list:
        text = spec.text_content()
        splited_list = text.split(":")
        if len(splited_list) >= 2:
            data_list.append(product_data.MustInfo(
                key=splited_list[0].strip(),
                valueList=[
                    splited_list[1].strip()
                ]
            ))
    return data_list

def parse_short_description(root: HtmlElement) -> str:
    return root.xpath('//div[@itemprop="description"]')[0].text_content()

def parse_title(root: HtmlElement) -> str:
    return root.xpath('//span[@itemprop="name"]')[0].text_content()

def parse_additional_data_list(root: HtmlElement) -> List[product_data.AdditionalProductList]:
    additional_list = root.xpath('//div[contains(@class, "amrelated-grid-wrapper")]//div[@class="box-image"]')
    data_list = []
    for additional_data in additional_list:
        img_elem = additional_data.xpath('.//img[@class="product-image-photo "]')
        img = img_elem[0].get('src')
        title_elem = additional_data.xpath('.//strong[@class="product-item-name"]/a')[0]
        goods_url = title_elem.get('href')
        product_id = goods_url.split('/')[-1].replace(".html", '')
        title = title_elem.get("title")
        data_list.append(product_data.AdditionalProductList(
            productId=product_id,
            goodsUrl=goods_url,
            productName=title,
            thumbnailImage=img
        ))
    return data_list

