import pytest
import pandas as pd

from models.product_data import BrandData
from shopify_dao.product import ProductDao
from supplier_manager.winsome.product_manager import WinsomeProductManager
from tests.supplier_manager.assertions import assert_base_data, assert_sku_fetch

product_path = 'datacollections/winsome/test.xlsx'
stock_path = 'datacollections/winsome/stocks.xlsx'
sku_prefix = "TEST"

@pytest.mark.asyncio()
async def test_convert_winsome(product_dao: ProductDao):
    with open("supplier_manager/andersonteak/warranty.html") as f:
        brand_data = BrandData(
            brandName="Winsome",
            warranty=f.read(),
        )
    wpm = WinsomeProductManager(
        product_dao,
        brand_data,
        product_path, 
        stock_path, 
        sku_prefix=sku_prefix
    )
    await wpm.upsert_all_product_data()
    product_data_list = await wpm.fetch_all_product_data_list()
    assert len(product_data_list) > 0
    assert_base_data(product_data_list, product_dao)
    


def test_fetch_single_row(product_dao: ProductDao, brand_data: BrandData):
    brand_data.brandName = "Vifah"
    wpm = WinsomeProductManager(
        product_dao,
        brand_data,
        product_path, 
        stock_path, 
        sku_prefix=sku_prefix
    )
    df: pd.DataFrame = pd.read_excel(product_path, header=2)
    sku = list(df['Item #'])[0]
    default_id = f"{sku_prefix}-{sku}"
    assert_sku_fetch(wpm, default_id)

