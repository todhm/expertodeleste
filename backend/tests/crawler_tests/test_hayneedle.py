from crawler.driver_utils import create_profile_driver
from crawler.hayneedle import parse_needle_data
from tests.utils import assert_set_data

def test_hayneedle_none_option():
    url = 'https://www.hayneedle.com/product/homesourceindustrieslyza3piececounterheightdiningset.cfm'
    driver = create_profile_driver()
    data = parse_needle_data(driver, url)
    print(data.skuList, data.price)
    assert_set_data(data)
    