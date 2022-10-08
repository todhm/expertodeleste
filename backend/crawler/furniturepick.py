import logging
from typing import List, Optional
import traceback
from datetime import datetime as dt

from selenium import webdriver  # Import from seleniumwire
from bs4 import BeautifulSoup

from models import product_data
from dataparser.tags import add_additional_tag_to_product


logger = logging.getLogger(__name__)



def parse_option_cases(pd: product_data.ProductData, driver: webdriver.Chrome) -> None:
    wrapper_elem = driver.find_element_by_xpath("//div[contains(@class, 'price-box-wrapper')]")
    price = float(wrapper_elem.find_element_by_xpath(".//meta[@itemprop='price']").get_attribute('content'))
    before_sales_price = float(wrapper_elem.find_element_by_xpath(
        ".//div[@class='price-box list-price']//span[@class='price']/span"
    ).get_attribute('textContent').replace(',', '').replace("$", ''))
    pd.beforeSalePrice = before_sales_price
    pd.price = price
    base_set_compositions = driver.find_elements_by_xpath('//div[@class="bundle-set"]//ul/li[contains(@class, "active")]')
    default_set_list = []
    for base_set in base_set_compositions:
        a_tag = base_set.find_element_by_xpath('.//a/img')
        image = a_tag.get_attribute("src")
        default_count = int(base_set.find_element_by_xpath('.//b').get_attribute("textContent"))
        name = base_set.get_attribute("textContent").replace(str(default_count), '').replace("x", '').strip()
        default_set_list.append(
            product_data.DefaultSetList(
                productName=name,
                defaultCount=default_count,
                thumbnailImage=image
            )
        )
    pd.defaultSetList = default_set_list
    option_list = driver.find_elements_by_xpath("//div[@id='product-options-wrapper']//ol/li[contains(@class, 'item')]")
    additional_product_list = []
    for sku_data in option_list:
        title_elem = sku_data.find_element_by_xpath(".//strong[@class='title']")
        title = title_elem.get_attribute("textContent").strip()
        goods_url = title_elem.find_element_by_xpath('./a').get_attribute('href')
        sku_id_elem = sku_data.find_element_by_xpath(".//span[contains(., 'ID:')]")
        sku_id = sku_id_elem.get_attribute("textContent")
        sku_id = sku_id.replace("ID:", "").strip()
        price_elem = sku_data.find_element_by_xpath(".//div[contains(@class, 'price') and contains(@class, 'active')]")
        price = float(price_elem.text.strip().replace("$", '').replace(",", ''))
        try:
            before_sale_price = float(price_elem.find_element_by_xpath('./span').get_attribute("textContent").replace("$", '').replace(",", ''))
        except Exception:
            before_sale_price = price
        img_tag = sku_data.find_element_by_xpath(".//div[@class='product-img']/a/img")
        img = img_tag.get_attribute("src")
        if img.endswith('.gif'):
            img_tag = sku_data.find_element_by_xpath(".//div[@class='product-img']/a")
            img = img_tag.get_attribute("href")
        additional_product_list.append(
            product_data.AdditionalProductList(
                productId=sku_id,
                goodsUrl=goods_url,
                productName=title,
                price=price,
                beforeSalePrice=before_sale_price,
                thumbnailImage=img
            )
        )    
    pd.additionalProductList = additional_product_list
    return

    
def parse_brand_data(driver: webdriver.Chrome) -> product_data.BrandData:
    brand_wrapper = driver.find_element_by_xpath('//div[@class="product-manufacturer"]')
    brand_name = brand_wrapper.find_element_by_xpath('.//h5/span[@itemprop="name"]').get_attribute("textContent").strip()
    brand_description = brand_wrapper.get_attribute("outerHTML")
    brand_image_elem = brand_wrapper.find_elements_by_xpath(".//a/img")
    brand_logo = brand_image_elem[0].get_attribute('src') if brand_image_elem else ""
    brand_data = product_data.BrandData(
        brandDescription=brand_description,
        brandName=brand_name,
        brandLogo=brand_logo

    )
    return brand_data
        

def return_mustinfo_list(driver: webdriver.Chrome) -> List[product_data.MustInfo]:
    must_info_list = []
    li_list = driver.find_elements_by_xpath("//div[contains(@class, 'product-details') and contains(., 'Additional Information')]//ul/li[@class='clearer']")
    for li_elem in li_list:
        title = li_elem.find_element_by_xpath("./div[@class='title']").get_attribute("textContent").strip()
        value = li_elem.find_element_by_xpath("./div[@class='description']").get_attribute("textContent").strip()
        must_info_list.append(
            product_data.MustInfo(
                key=f"{title}",
                valueList=[value]
            )
        )
    li_list = driver.find_elements_by_xpath("//div[@class='product-dimensions']//ul/li")
    for li_elem in li_list:
        title = li_elem.find_element_by_xpath("./div[@class='title']").get_attribute("textContent").strip()
        if title == 'Product Name':
            continue
        weight = li_elem.find_element_by_xpath("./div[@class='weight']").get_attribute("textContent").strip()
        must_info_list.append(
            product_data.MustInfo(
                key=f"{title} WEIGHT",
                valueList=[weight]
            )
        )
        dimensions = li_elem.find_element_by_xpath("./div[@class='dimensions']").get_attribute("textContent").strip()
        if dimensions:
            must_info_list.append(
                product_data.MustInfo(
                    key=f"{title} DIMENSIONS",
                    valueList=[dimensions]
                )
            )
        else:
            dimension_list = li_elem.find_element_by_xpath("./div[@class='additional']").get_attribute("innerHTML").strip().split("<br>")
            must_info_list.append(
                product_data.MustInfo(
                    key=f"{title} DIMENSIONS",
                    valueList=dimension_list
                )
            )

    return must_info_list


def return_review_list_from_data(driver: webdriver.Chrome) -> List[product_data.ReviewData]:
    review_data_list = []
    review_list = driver.find_elements_by_xpath("//div[@class='product-reviews']//dl[@itemprop='review']")
    for review_elem in review_list:
        review_score = float(
            review_elem.find_element_by_xpath(
                ".//div[@class='reviews-summary']/meta[@itemprop='ratingValue']"
            ).get_attribute("content")
        )
        review_content = review_elem.find_element_by_xpath(
            ".//span[@class='review-content']"
        ).get_attribute("textContent")
        review_images_elem_list = review_elem.find_elements_by_xpath('.//div[@class="customer-pictures"]/ul/li/a')
        author_full_text = review_elem.find_element_by_xpath(
            ".//div[@class='author']"
        ).get_attribute("textContent").replace('by', '').strip()
        author = author_full_text.split("on")[0]
        review_time = dt.strftime(dt.strptime(author_full_text.split("on")[1].strip(), "%B %d, %Y"), "%Y-%m-%d %H:%M:%S")
        review_image_list = [x.get_attribute('href') for x in review_images_elem_list]
        review_data_list.append(product_data.ReviewData(
            reviewTitle="",
            reviewText=review_content,
            reviewPoint=review_score,
            reviewImageList=review_image_list,
            writer=author,
            reviewTime=review_time
        ))
    return review_data_list


def return_question_list(driver: webdriver.Chrome) -> List[product_data.QuestionData]:
    question_data_list = []
    question_list = driver.find_elements_by_xpath("//div[@class='product-questions']//ul/li")
    for question_elem in question_list:
        question = question_elem.find_element_by_xpath(".//div[@class='question']").get_attribute("textContent")
        author = question_elem.find_element_by_xpath(".//div[@class='question']/span").get_attribute("textContent").replace('Asked by', '').strip()
        question = question.replace(f"Asked by {author}", '').strip()
        answer = question_elem.find_element_by_xpath(".//div[@class='answer']").get_attribute("textContent").replace('\xa0', '').strip()
        question_data_list.append(
            product_data.QuestionData(
                questionTitle=question,
                answer=answer,
                writer=author,
            )
        )
    return question_data_list


def parse_furniturepick_data(driver: webdriver.Chrome, url: str, additional_product: Optional[product_data.AdditionalProductList] = None) -> product_data.ProductData:
    try:
        pd = product_data.ProductData(goodsUrl=url)
        driver.get(url)
    except Exception:
        message = f"Error while fetching requests data {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)
    try:
        atag_list = driver.find_elements_by_xpath("//div[@id='itemslider-zoom']//a[contains(@class, 'cloud-zoom-gallery')]")
        pd.mainImageList = [x.get_attribute('href') for x in atag_list]
        title_elem = driver.find_element_by_xpath("//div[@class='product-name']/h1")
        pd.goodsName = title_elem.get_attribute("textContent")
        product_tab = driver.find_element_by_xpath('//div[@id="product-tabs"]//div[contains(@class, "product-details")]')
        description = product_tab.get_attribute("outerHTML")
        soup = BeautifulSoup(description, 'html.parser')
        atag_list = soup.findAll('a')
        for atag in atag_list:
            atag['href'] = "#!"
        pd.description = str(soup)
        pd.brandName = driver.find_element_by_xpath('//h5[@itemprop="brand"]').get_attribute("textContent")
        pd.productId = driver.find_element_by_xpath('//div[@class="sku"]/meta[@itemprop="sku"]').get_attribute("content")
    except Exception:
        message = f"Error while parsing image product data {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)
    
    
    try:
        pd.goodsMustInfo = return_mustinfo_list(driver)
    except Exception:
        message = f"Error while parsing must info {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)
    
    try:
        if additional_product is None:
            parse_option_cases(pd, driver)
        else:
            pd.beforeSalePrice = additional_product.beforeSalePrice
            pd.price = additional_product.price
    except Exception:
        message = f"Error while parsing option info {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)

    try:
        pd.brandData = parse_brand_data(driver)
    except Exception:
        message = f"Error while parsing brand info {url}"
        logger.error(message)
        raise ValueError(message)
        
    try:
        pd.reviewList = return_review_list_from_data(driver)
    except Exception:
        message = f"Error while parsing review info {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)
    try:
        pd.questionList = return_question_list(driver)
    except Exception:
        message = f"Error while parsing review info {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)
    try:
        if additional_product is None:
            add_additional_tag_to_product(pd)
    except Exception:
        message = f"Error while parsing additional tags {url} {traceback.format_exc()}"
        logger.error(message)
        raise ValueError(message)
    return pd


