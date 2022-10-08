from crawler.driver_utils import create_profile_driver
from crawler.alli import AlliCrawlHandler
from commissions.alli import convert_alli_commissions
from tests.utils import assert_set_data


def test_alli_crawl_bulk_data_error():
    url = 'https://www.aliexpress.com/item/4001313066385.html'
    driver = create_profile_driver()
    ach = AlliCrawlHandler(driver)
    product_data = ach.parse_crawl_data(url)
    product_data = convert_alli_commissions(product_data)
    assert_set_data(product_data, sku_length=1)
    assert product_data.price > product_data.cost
    for sku in product_data.skuList:
        assert sku.price > sku.cost


def test_alli_crawl_delivery_error():
    url = 'https://es.aliexpress.com/item/3256803170155316.html'
    driver = create_profile_driver()
    ach = AlliCrawlHandler(driver)
    product_data = ach.parse_crawl_data(url)
    product_data = convert_alli_commissions(product_data)
    assert_set_data(product_data, sku_length=3)
    assert product_data.price > product_data.cost
    for sku in product_data.skuList:
        assert sku.price > sku.cost


def test_alli_crawl_multitime_cases():
    url = 'https://es.aliexpress.com/item/3256803299756688.html?spm=a2g0o.productlist.0.0.407460904jdunG&algo_pvid=55d4dead-7c7c-4db4-b796-0cf938165304&algo_exp_id=55d4dead-7c7c-4db4-b796-0cf938165304-0&pdp_ext_f=%7B%22sku_id%22%3A%2212000026008873728%22%7D&pdp_npi=2%40dis%21USD%21%215.36%21%21%21%21%21%40210318cb16569353137236878e9b7c%2112000026008873728%21sea'
    second_url = 'https://es.aliexpress.com/item/3256803170155316.html'
    driver = create_profile_driver()
    ach = AlliCrawlHandler(driver)
    product_data = ach.parse_crawl_data(url)
    product_data = ach.parse_crawl_data(second_url)
    product_data = convert_alli_commissions(product_data)
    assert_set_data(product_data, sku_length=3)
    assert product_data.price > product_data.cost
    for sku in product_data.skuList:
        assert sku.price > sku.cost