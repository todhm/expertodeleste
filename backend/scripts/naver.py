from typing import List
from crawler.smartstore import crawl_product
from models.product_data import ProductData
from translation.translation_dao import TranslationDao
from exchange_rate.exchange_rate_dao import ExchangeRateDao
from dataparser.image import upload_urls_to_s3_list
from dataparser.htmlparser import HtmlParserDao
from dataparser.numbers import round_up_decimals


async def naver_smartstore_script(
    link:str, 
    brand_name: str = "smartstorebrrand",
    product_id: str = "",
    goods_name: str = "",
    tag_list: List[str] = [],
) -> ProductData:
    if not product_id:
        last_id = link.split("/")[-1]
        product_id = last_id.split("?")[0].strip()
    td = TranslationDao('ko', 'es')
    product_data = crawl_product(link)
    product_data.productId = product_id
    for tag in tag_list:
        product_data.add_tag(tag)
    product_data.mainImageList = await upload_urls_to_s3_list(
        product_data.mainImageList,
        folder_prefix=f'/{brand_name}',
        quality=90,
        fix_image_width=775
    )
    hpd = HtmlParserDao(product_data.description)
    origiinal_url_list = hpd.extract_html_image_list()
    new_image_list = await upload_urls_to_s3_list(
        product_data.mainImageList,
        folder_prefix=f'/{brand_name}/{product_data.productId}',
        quality=90,
        fix_image_width=775
    )
    image_map = {key: val for key,val in  zip(origiinal_url_list, new_image_list)}
    product_data.description = hpd.change_image_description(image_map)    
    await td.translate_product(product_data)
    exd = ExchangeRateDao()
    product_data.cost = exd.calculate_exchange_rate(product_data.cost)
    product_data.price = round_up_decimals(1.25 * product_data.cost)
    if goods_name:
        product_data.goodsName = goods_name
    return product_data
