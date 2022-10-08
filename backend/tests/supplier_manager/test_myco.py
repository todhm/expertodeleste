import pytest
import pandas as pd

from models.product_data import BrandData
from shopify_dao.product import ProductDao
from supplier_manager.art.product_manager import ArtProductManager
from tests.supplier_manager.assertions import assert_base_data, assert_sku_fetch
from data_types.brand_types import ART_FURNITURE


@pytest.mark.asyncio()
async def test_convert_myco(product_dao: ProductDao, brand_data: BrandData):
    brand_data.brandName = ART_FURNITURE
    wpm = ArtProductManager(
        product_dao,
        brand_data,
        product_path='datacollections/art/test.xlsx',
        stock_path='datacollections/art/inventory.xlsx',
        sku_prefix="TEST"
    )
    await wpm.upsert_all_product_data()
    product_data_list = await wpm.fetch_all_product_data_list()
    assert len(product_data_list) > 0
    assert_base_data(product_data_list, product_dao)


def test_fetch_single_row(product_dao: ProductDao, brand_data: BrandData):
    product_path = 'datacollections/art/test.xlsx'
    product_df = pd.read_excel(product_path)
    sku_prefix = "TEST"
    wpm = ArtProductManager(
        product_dao,
        brand_data,
        product_path=product_path,
        stock_path='datacollections/manhattan/inventory.xlsx',
        sku_prefix="TEST"
    )
    sku = list(product_df['Model '])[0]
    default_id = f"{sku_prefix}-{sku}"
    assert_sku_fetch(wpm, default_id)

