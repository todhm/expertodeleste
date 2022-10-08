import pandas as pd
from models.product_data import BrandData
from shopify_dao.product import ProductDao
from supplier_manager.andersonteak.product_manager import AndersonTeakProductManager
from tests.supplier_manager.assertions import assert_base_data, assert_sku_fetch


def test_convert_anderson_product(product_dao: ProductDao, brand_data: BrandData):
    atpm = AndersonTeakProductManager(
        product_dao,
        brand_data,
        'datacollections/andersonteak/testproducts.xlsx', 
        'datacollections/andersonteak/testinventory.csv',
        sku_prefix="TEST"
    )
    atpm.upsert_all_anderson_data()
    product_data_list = atpm.fetch_all_product_data_list()
    assert len(product_data_list) > 0
    assert_base_data(product_data_list, product_dao)


def test_fetch_single_row(product_dao: ProductDao, brand_data: BrandData):
    product_path = 'datacollections/andersonteak/testproducts.xlsx'
    xls = pd.ExcelFile(product_path)
    product_df: pd.DataFrame = pd.read_excel(xls, 'Bulkload', header=1).dropna(subset=['Product Name']).reset_index(drop=True)
    sku_prefix = "TEST"
    atpm = AndersonTeakProductManager(
        product_dao,
        brand_data,
        product_path, 
        'datacollections/andersonteak/testinventory.csv',
        sku_prefix=sku_prefix
    )
    sku = list(product_df['Manufacturer Model Number'])[0]
    default_id = f"{sku_prefix}-{sku}"
    assert_sku_fetch(atpm, default_id)

