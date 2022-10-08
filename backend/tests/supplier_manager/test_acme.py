import pytest
import pandas as pd

from models.product_data import BrandData
from shopify_dao.product import ProductDao
from supplier_manager.acme.product_manager import AcmeProductManager
from tests.supplier_manager.assertions import assert_base_data, assert_sku_fetch


@pytest.mark.asyncio()
async def test_convert_acme_product(product_dao: ProductDao, brand_data: BrandData):
    apm = AcmeProductManager(
        product_dao,
        brand_data,
        'datacollections/acme/test.csv', 
        'datacollections/acme/images.csv', 
        'datacollections/acme/price.csv', 
        sku_prefix="TEST"
    )
    await apm.upsert_all_acme_data()
    product_data_list = await apm.fetch_all_product_data_list()
    assert len(product_data_list) > 0
    for cushion_data in product_data_list:
        assert len(cushion_data.shopifyId) > 0
        assert len(cushion_data.tagList) > 0
        assert len(cushion_data.productType) > 0
        assert len(cushion_data.featureList) > 0
        assert len(cushion_data.shortDescription) > 0
        product_dao.delete_product(cushion_data.productId)
    

@pytest.mark.asyncio()
async def test_fetch_single_row(product_dao: ProductDao, brand_data: BrandData):
    product_path = 'datacollections/acme/test.csv'
    sku_prefix = "TEST"
    apm = AcmeProductManager(
        product_dao,
        brand_data,
        product_path, 
        'datacollections/acme/images.csv', 
        'datacollections/acme/price.csv', 
        sku_prefix=sku_prefix
    )
    df = pd.read_csv(product_path)
    test_sku = list(df['acme.sku'])[0]
    test_sku = f"{sku_prefix}-{test_sku}"
    assert_sku_fetch(apm, test_sku)