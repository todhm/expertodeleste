from typing import List, Dict
import re
import json
import logging
import traceback
import time
from random import randrange

from selenium import webdriver
import requests

from models.product_data import ProductData, DeliveryData, MustInfo
from data_types import alli_data_types
from .alli_data_parser import (
    parse_none_option_price,
    parse_option_name_list, parse_sku_list, 
    return_mobile_goods_description,
    return_pc_json_data,
    make_review_url,
    parse_review_page
)

logger = logging.getLogger(__name__)


class AlliCrawlHandler(object):

    base_url = "https://m.aliexpress.com"
    base_pc_url = "https://aliexpress.com"


    def __init__(self, driver: webdriver.Chrome, country_code: str = alli_data_types.US_COUNTRY_CODE):
        self.driver: webdriver.Chrome = driver
        self.page_idx = 0
        self.country_code = country_code
        
    def return_mobile_data_json(
        self,
        link: str,
        alli_id: str,
    ):
        driver_cookies = self.driver.get_cookies()
        cookies = {c['name']: c['value'] for c in driver_cookies}
        headers = {
            'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': link,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'
        }
        apiurl = f'{self.base_url}/api/products/{alli_id}/fetch'
        apidata = json.loads(
            requests.get(
                apiurl,
                cookies=cookies, headers=headers
            ).text
        )['data']
        return apidata

    def close_inital_modal(self):
        modal_data = self.driver.find_elements_by_xpath('//img[@class="smb-dialog-btn__close"]')
        if modal_data:
            modal_data[0].click()
        self.page_idx = -1

    def parse_title(self, apidata: Dict) -> str:
        if (
            not apidata['productInfo'].get('subject')
        ) and (
            apidata['productInfo']['productType'] == 0
        ) and apidata['productInfo']['status'] == 4:
            raise ValueError("product soldout")
        if not apidata['productInfo'].get("subject"):
            raise ValueError(apidata['productInfo'])
        return apidata['productInfo']['subject']

    def parse_delivery_soup(self) -> Dict:
        dynamic_shipping_list = self.driver.find_elements_by_xpath('//div[contains(@class, "comet-modal-body")]//div[@class="dynamic-shipping"]')
        for x in dynamic_shipping_list:
            trackable_span = x.find_elements_by_xpath(".//*[contains(text(), '추적 가능') or contains(text(), 'Tracking Available') or contains(text(), 'disponible')]")
            if trackable_span:
                price_span_list = x.find_elements_by_xpath('.//div[contains(@class, "dynamic-shipping-titleLayout")]')
                price_text = ""
                for price_span in price_span_list:
                    price_text += price_span.text
                price_span = x.find_elements_by_xpath('.//div[contains(@class, "dynamic-shipping-titleLayout")]')
                company_span = x.find_element_by_xpath('.//div[contains(@class, "dynamic-shipping-contentLayout")][2]')
                company = company_span.get_attribute("textContent")
                if '무료' in price_text or 'free' in price_text.lower() or 'gratis' in price_text.lower():
                    price = 0
                elif price_span:
                    price_span = price_span[0]
                    price = re.search(r'.*\:(.*)', price_span.text).group(1)
                else:
                    continue
                if 'saver' in company.lower() or 'cainiao' in company.lower() or 'savor' in company.lower():
                    continue
                data_object = {}
                data_object['price'] = price
                data_object['company'] = company
                return data_object

    def change_delivery_string(self, price: str) -> float:
        if str(price).isdigit():
            price = float(price)
            return price
        else:
            if 'free' in str(price).lower():
                return 0
            price = (
                str(price)
                .replace('₩', '').replace('원', '').replace(',', '').replace(' ', '')
                .replace("\\", "").replace("'", "")
            )
            if '무료' in price:
                price = 0
            if re.search(r'(\d+)', price):
                price = re.search(r'(\d+)', price).group(1)
            return float(price)

    def parse_mobile_delivery_data(self, apidata: Dict) -> Dict:
        try:
            korean_freeshiping_case = (
                (
                    apidata['freightInfo']['defaultFreight']['sendGoodsCountry'] == 'CN'
                ) and (
                    apidata['freightInfo']['defaultFreight']['tracking']
                )
            )
            us_freeshiping_case = (
                (
                    apidata['freightInfo']['defaultFreight']['sendGoodsCountry'] == 'US'
                ) and (
                    apidata['freightInfo']['defaultFreight']['tracking']
                ) and (
                    self.country_code == alli_data_types.US_COUNTRY_CODE
                )
            )
            if korean_freeshiping_case or us_freeshiping_case:
                price = apidata['freightInfo']['defaultFreight']['freightAmount']['value']
                company = apidata['freightInfo']['defaultFreight']['company']
                days = apidata['freightInfo']['defaultFreight']['time']
                if 'savor' in company.lower() or 'cainiao' in company.lower():
                    raise ValueError("Not good shipping")
                return {
                    'price': price,
                    'company': company,
                    'days': days
                }
        except Exception:
            pass

        try:
            sleeptime_1 = randrange(1, 2)
            time.sleep(sleeptime_1)
            script = """var productShippingInfoList = document.getElementsByClassName('product-dynamic-shipping-moreOptions');
                        if(productShippingInfoList.length){
                            productShippingInfoList[0].click();
                        }else{
                            var productShippingInfoList = document.getElementsByClassName('product-shipping-info');
                            if(productShippingInfoList.length){
                               productShippingInfoList[0].click();
                            }
                        }
                        """
            self.driver.execute_script(script)
            sleeptime_1 = randrange(1, 2)
            time.sleep(sleeptime_1)
        except Exception:
            script = """ var deliveryInfoList =  document.getElementsByClassName('sku-property');
                        for(var i=0;i<deliveryInfoList.length;i++){
                            var deliveryInfo=deliveryInfoList[i];
                            if(deliveryInfo.children){
                                var optionName = deliveryInfo.children[0].textContent;
                                if(optionName.includes('Ships From:')){
                                    var childrenElem = deliveryInfo.children[1];
                                    for(var k=0;k<childrenElem.children.length;k++){
                                        finalElem = childrenElem.children[k]
                                        if(finalElem&&finalElem.textContent.includes('중국')||finalElem.textContent.includes('CN')){
                                            finalElem.click()
                                            break;
                                        }
                                    }                                                    
                                }
                            }
                        }"""
            self.driver.execute_script(script)
            sleeptime_1 = randrange(1, 2)
            time.sleep(sleeptime_1)
            script = """var productShippingInfoList = document.getElementsByClassName('product-shipping-info');
            productShippingInfoList[0].click()"""
            self.driver.execute_script(script)
            sleeptime_1 = randrange(1, 2)
            time.sleep(sleeptime_1)

        script = """
        var nextDialogClose = document.getElementsByClassName('next-icon-select');
        if(nextDialogClose.length){nextDialogClose[0].parentElement.parentElement.click()}
        """
        self.driver.execute_script(script)
        time.sleep(2)
        script = """
        var nextDialogClose = document.getElementsByClassName('next-dialog-footer');
        if(nextDialogClose.length){nextDialogClose[0].children[0].click()}
        """
        self.driver.execute_script(script)
        xpath = '//div[contains(@class, "comet-modal-body")]/button'
        more_option_btn_list = self.driver.find_elements_by_xpath(xpath)
        if more_option_btn_list:
            more_option_btn_list[0].click()
        delivery_object = self.parse_delivery_soup()
        script = """
            var nextDialogClose = document.getElementsByClassName('next-icon-add');
            if(nextDialogClose.length){nextDialogClose[0].click()}
        """
        self.driver.execute_script(script)
        script = """
            var nextDialogClose = document.getElementsByClassName('comet-modal-close');
            if(nextDialogClose.length){nextDialogClose[0].click()}
        """
        self.driver.execute_script(script)
        time.sleep(1)
        delivery_object['price'] = self.change_delivery_string(delivery_object['price'])
        return delivery_object

    def set_mobile_price_data(self, apidata: Dict, product_data: ProductData) -> ProductData:
        try:
            option_name_list = parse_option_name_list(apidata)
            promotion_price = 0
            if self.driver.find_elements_by_xpath("//div[@class='coupon-mark-new']") and apidata.get('promotionInfo'):
                promotion_price = self.driver.find_element_by_xpath("//div[@class='coupon-mark-new']").text
                promotion_price = int(re.search(r"\$(\d+)",promotion_price).group(1))
            elif (
                self.driver.find_elements_by_xpath("//div[@class='uniform-banner-box-right']") 
                and 
                not self.driver.find_elements_by_xpath("//div[@class='uniform-banner-box-right']/div[contains(@class, 'countDown')]") 
            ):
                if apidata.get('promotionInfo') and apidata['promotionInfo'].get("newUserCoupon"):
                    promotion_price = float(apidata['promotionInfo']['newUserCoupon']['denomination'].replace("₩", "").replace(",", ''))
                else:
                    promotion_price = 6000
            product_data.optionNameList = option_name_list
        except Exception as e:
            raise ValueError("Error while get option names" + str(e))

        try:
            if not option_name_list:
                price, stock = parse_none_option_price(apidata)
                product_data.stock = stock
                product_data.trackInventory = True
                is_sold_out = stock == 0
                if is_sold_out:
                    raise ValueError("No available stocks")
                product_data.isSoldOut = is_sold_out
                product_data.cost = price + promotion_price
                return product_data
        except Exception:
            raise ValueError(f"Error while parsing none option data {traceback.format_exc()}")

        try:
            
            sku_list = parse_sku_list(
                apidata,
                promotion_price=promotion_price,
                option_name_list=option_name_list
            )
            product_data.skuList = sku_list
            min_price = min([x.cost for x in sku_list])
            product_data.cost = min_price
        except Exception:
            raise ValueError(f"Error occured parsing option data list {traceback.format_exc()}")

        if not sku_list:
            raise ValueError("Cannot make option data")
        if sku_list:
            available_option_list = [x for x in sku_list if not x.isSoldOut]
            if not available_option_list:
                raise ValueError("All option sold out")
    
    def set_mobile_goods_description(self, product_data: ProductData, apidata: Dict = {}) -> None:
        goods_description = return_mobile_goods_description(apidata)
        product_data.description = goods_description

    def return_review_page(
        self,
        link: str,
        url: str,
    ):
        driver_cookies = self.driver.get_cookies()
        cookies = {c['name']: c['value'] for c in driver_cookies}
        headers = {
            'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': link,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'
        }
        return requests.get(
            url,
            cookies=cookies,
            headers=headers
        ).text


    def parse_crawl_data(
        self,
        link: str,
        **kwargs
    ) -> ProductData:
        product_data = ProductData(
            goodsUrl=link
        )
        try:
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                    })
                """
            })
            regex = r"aliexpress.com/item/([0-9]+).html"
            alli_id = re.search(regex, link).group(1)
            self.driver.get(link)
        except Exception:
            error_message = f"Error while get page {link}" + traceback.format_exc()
            logger.error(error_message)
            # raise ValueError(error_message)
        try:
            product_data.productId = alli_id
            apidata = self.return_mobile_data_json(
                link,
                alli_id=alli_id,
            )
        except Exception:
            error_message = f"Error while fetching alli api {product_data.goodsUrl} " + traceback.format_exc()
            logger.error(error_message)
            raise ValueError(error_message)

        try:
            time.sleep(2)
            if self.page_idx == 0:
                self.close_inital_modal()
        except Exception:
            logger.error("Error while click modal " + product_data.goodsUrl + traceback.format_exc())
        try:
            title = self.parse_title(apidata)
            product_data.goodsName = title
        except Exception:
            error_message = "error cannot parse basic object " + product_data.goodsUrl + traceback.format_exc()
            logger.error(error_message)
            self.driver.save_screenshot("error.png")
            raise ValueError(error_message)

        try:
            
            main_image_list = apidata['productInfo']['imageList']
            product_data.mainImageList = main_image_list
        except Exception:
            error_message = 'main image parsing error ' + product_data.goodsUrl + traceback.format_exc()
            logger.error(error_message)
            raise ValueError(error_message)


        try:
            self.set_mobile_price_data(apidata, product_data)
        except ValueError as ve:
            logger.error(str(ve) + product_data.goodsUrl)
            raise ve
        except Exception as e:
            logger.error("unexpected option error " + str(e) + product_data.goodsUrl)
            raise ValueError("unexpected option error " + str(e) + product_data.goodsUrl)

        try:
            delivery_object = self.parse_mobile_delivery_data(apidata)
            product_data.deliveryDataList = [DeliveryData(
                cost=delivery_object['price'],
                deliveryName=delivery_object['company'],
                deliveryDescription=delivery_object.get('days', ''),
            )]
        except Exception:
            self.driver.save_screenshot("error.png")
            error_message = "error cannot parse delivery object " + product_data.goodsUrl + traceback.format_exc()
            logger.error(error_message)
            raise ValueError(error_message)


        try:
            self.set_mobile_goods_description(product_data, apidata)
        except Exception as e:
            logger.error('unexpected goods description Error' + str(e) + product_data.goodsUrl)
            raise ValueError('unexpected goods description Error' + str(e) + product_data.goodsUrl)

        try:
            pcurl = f'{self.base_pc_url}/item/{alli_id}.html'
            if self.country_code == alli_data_types.KOREA_COUNTRY_CODE:
                pc_data = return_pc_json_data(self.driver, pcurl)
            else:
                pc_data = None
        except Exception:
            error_message = f"Error while parsing pc data {product_data.goodsUrl} " + traceback.format_exc()
            logger.error(error_message)
            pc_data = None

        try:
            specification_list = []
            # 영어로 상품을 가져올경우 상품상세정보는 모바일페이지에서만 가져다씀
            if pc_data and self.country_code == alli_data_types.KOREA_COUNTRY_CODE:
                spec_list = pc_data['specsModule']['props']
            else:
                spec_list = apidata['specificationInfo']['propertyList']
            for data in spec_list:
                key_string = data['attrName'].replace('.', '')
                specification_list.append(MustInfo(key=key_string, valueList=[data['attrValue']]))
            product_data.goodsMustInfo =  specification_list
        except Exception:
            logger.error(f'mobile goods must info error {product_data.goodsUrl}')
            pass
        
        try:
            review_url = make_review_url(alli_id, apidata)
            review_html = self.return_review_page(
                self.driver.current_url,
                review_url
            )
            product_data.reviewList = parse_review_page(review_html)
        except Exception:
            logger.error('mobile order count error')
            pass

        return product_data