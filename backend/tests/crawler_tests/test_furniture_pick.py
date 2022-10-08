from venv import create
from crawler.furniturepick import parse_furniturepick_data
from crawler.driver_utils import create_profile_driver
from tests.utils import assert_set_data

def test_furniture_pick_crawl():
    url = 'https://www.furniturepick.com/modern-authentic-rectangular-dining-room-set-accentrics-home-ah-d192-132b-t-ds-d192-144-538.html'
    driver = create_profile_driver()
    data = parse_furniturepick_data(driver, url)
    key_exists_pairs = [{
        "key": "Modern Authentic Rectangular Dining Table",
        "exists": False,
    },{
        "key": "Color Group",
        "exists": False,
    }]
    assert_set_data(data, default_set_length=2, additional_set_length=5, key_exists_pairs=key_exists_pairs)
    for additional_data in data.additionalProductList:
        new_data = parse_furniturepick_data(driver, additional_data.goodsUrl, additional_product=additional_data)
        assert_set_data(new_data)
        
        

def test_furniture_pick_crawl_with_reviews():
    url = 'https://www.furniturepick.com/carriage-house-breakfast-nook-set-sunny-designs-su-0113ec-t-0113ec-bl-bs.html'
    driver = create_profile_driver()
    data = parse_furniturepick_data(driver, url)
    assert_set_data(data, default_set_length=2, additional_set_length=5, tag_check_list=["Big"])
    for additional_data in data.additionalProductList:
        new_data = parse_furniturepick_data(driver, additional_data.goodsUrl, additional_product=additional_data)
        assert_set_data(new_data)
    
def test_furniturepick_error_case():
    url = 'https://www.furniturepick.com/carmen-dining-room-set-white-esf-furniture-ef-carmentablewhite-carmensidechairwhite.html'
    driver = create_profile_driver()
    data = parse_furniturepick_data(driver, url)
    data = parse_furniturepick_data(driver, url)
    assert_set_data(data, default_set_length=2, additional_set_length=5, tag_check_list=["Big"])
    for additional_data in data.additionalProductList:
        new_data = parse_furniturepick_data(driver, additional_data.goodsUrl, additional_product=additional_data)
        assert_set_data(new_data)