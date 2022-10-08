import pytest
from crawler.smartstore import crawl_product
from translation.translation_dao import TranslationDao


@pytest.mark.asyncio()
async def test_translate_description(test_app):
    link = 'https://shopping.naver.com/department/stores/1000021107/products/2014705653'
    td = TranslationDao('ko', 'es')
    product_data = crawl_product(link)
    await td.translate_product(product_data)

    with open('datacollections/testtranslation.html', 'w') as f:
        f.write(product_data.description)
