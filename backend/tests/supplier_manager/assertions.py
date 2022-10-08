from typing import List

from models.product_data import ProductData
from shopify_dao.product import ProductDao
from supplier_manager.default_product_manager import DefaultProductManager


def assert_base_data(product_data_list: List[ProductData], product_dao: ProductDao):
    for cushion_data in product_data_list:
        assert len(cushion_data.shopifyId) > 0
        assert len(cushion_data.tagList) > 0
        assert len(cushion_data.productType) > 0
        assert len(cushion_data.featureList) > 0
        assert len(cushion_data.shortDescription) > 0
        assert len(cushion_data.weightInfoList) >= 1
        assert len(cushion_data.goodsMustInfo) >= 3
        # product_dao.delete_product(cushion_data.productId)
    

def assert_sku_fetch(supplier_manager: DefaultProductManager, sku_id: str):
    result = supplier_manager.fetch_single_row(sku_id)
    assert type(result) is dict
    assert len(result.keys()) > 0