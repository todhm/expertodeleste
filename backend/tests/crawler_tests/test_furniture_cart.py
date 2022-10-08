from crawler.furniturecart import parse_furniturecart_data
from crawler.driver_utils import create_profile_driver
from tests.utils import assert_set_data

def test_furniture_cart_crawl():
    url = 'https://www.furniturecart.com/berkshire-ervin-rectangular-dining-room-set-011-744-011-636-american-drew.html#'
    driver = create_profile_driver()
    data = parse_furniturecart_data(driver, url)
    key_exists_pairs = [{
        "key": "Style",
        "exists": False,
    },{
        "key": "Type",
        "exists": False,
    }, {
        "key": "Berkshire Ervin Rectangular Dining Table",
        "exists": False
    }]

    assert_set_data(data, default_set_length=2, additional_set_length=4, key_exists_pairs=key_exists_pairs)
    for additional_data in data.additionalProductList:
        new_data = parse_furniturecart_data(driver, additional_data.goodsUrl, additional_product=additional_data)
        assert_set_data(new_data)


def test_furniture_cart_error_case():
    url = 'https://www.furniturecart.com/morrissey-wallen-54-inch-adjustable-dining-set-w-bolan-party-chairs-218225-272754-2727bs-218218-2727-art-furniture.html'
    driver = create_profile_driver()
    data = parse_furniturecart_data(driver, url)
    assert_set_data(data, default_set_length=2, additional_set_length=3, key_exists_pairs=[])