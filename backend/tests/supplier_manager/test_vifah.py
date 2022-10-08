import pytest
import numpy as np
import pandas as pd

from models.product_data import BrandData
from shopify_dao.product import ProductDao
from supplier_manager.vifah.product_manager import VifahProductManager
from tests.supplier_manager.assertions import assert_base_data, assert_sku_fetch

product_path = 'datacollections/vifah/testhome.xlsx'
outdoor_path = 'datacollections/vifah/testoutdoor.xlsx'
office_path = 'datacollections/vifah/testoffice.xlsx'
inventory_path = 'datacollections/vifah/inventory.csv'
sku_prefix = "TEST"


@pytest.mark.asyncio()
async def test_convert_vifah(product_dao: ProductDao, brand_data: BrandData):
    brand_data.brandName = "Vifah"
    wpm = VifahProductManager(
        product_dao,
        brand_data,
        product_path, 
        outdoor_path, 
        office_path, 
        inventory_path, 
        sku_prefix=sku_prefix
    )
    await wpm.upsert_all_product_data()
    product_data_list = await wpm.fetch_all_product_data_list()
    assert len(product_data_list) > 0
    assert_base_data(product_data_list, product_dao)
    

def test_vifah_weight_parser():
    nan = np.nan
    data =  {
        'SKU': 'V817SET3', 
        'EAN/UPC': 8935083294621,
        'Brand': 'VIFAH',
        'Product Name': 'Riley Mid-Century 5-Piece  Indoor Walnut Metal Bar Set with Gray Seats',
        'Color': 'Powder coating Metal,  MDF with melamine top, \nFaux leather Upholstery',
        'Product Images': nan,
        'Product Specification.L': 'Table: 41L X 22W X 34H (inches) X 30 lbs\nStools: 18L X 14W X 24H (inches) X 11.2 lbs',
        'Product Specification.W': nan,
        'Product Specification.H': nan,
        'Product Dims': nan,
        'Packaging Specification.L': 'Box 1: 44L X 25W X 5H (inches) X 36 lbs\nBox 2,3: 25L X 20W X 13H (inches) X 29 lbs',
        'Packaging Specification.W': nan, 
        'Packaging Specification.H': nan, 
        'Package Dims': nan,
        'Total weight': 94,
        'cost': 451.67999999999995,
        'shippingCost': 125.19,
        'MAP': 587,
        'Description': "Riley", 
        'Features': 'Used as bar',
        'Specifications': nan, 
        'Country of origin': 'Vietnam', 
        'Shipping': 'Ground',
        'Image 1': 'https://www.dropbox.com/s/zvusucbvmbw4e96/V817SET3.jpg?dl=0', 
        'Image 2': 'https://www.dropbox.com/s/x1f2usmno58yalw/V817SET3_1.jpg?dl=0',
        'Image 3': 'https://www.dropbox.com/s/2dhftijrte2go5n/V817SET3_2.jpg?dl=0',
        'Image 4': 'https://www.dropbox.com/s/69o940of8j1ww2r/V817_dim.jpg?dl=0',
        'Image 5': 'https://www.dropbox.com/s/j8gfum1ka7vw9qy/V814_dim.jpg?dl=0',
        'Image 6': nan, 'Image 7': nan, 'MPN': nan, 'Finish': nan, 'Product Specification.LBS': nan, 'Packaging Specification.LBS': nan, 'Features and Specification': nan, 'LTL/Ground': nan, 'Full folder link': nan, 'Assembly instruction': nan, 'AI Video 1': nan, 'AI Video 2': nan, 'Inner Cubic Feet': nan, 'Inner Quarts': nan, "INNER PLANTER'S SIZE": nan, 'Special features': nan, 'Video': nan, 'QUANTITY': 230.0, 'ETA': nan, 'DISCONTINUED(YES/ NO)': 'No'}
    result = VifahProductManager.parse_weight_info(data)
    assert len(result) > 0


def test_vifah_weight_parser_error_case_seconds():
    nan = np.nan
    data =  {
        'SKU': 'V817SET3', 
        'EAN/UPC': 8935083294621,
        'Brand': 'VIFAH',
        'Product Specification.L': 'Product Dimension:Table: 91"L x 39"W x 29"H x 68 lbs\nFolding chair: 23"L x 26"W x 44"H x 18 lbs',
        'Product Specification.W': nan,
        'Product Specification.H': nan,
        'Product Dims': nan,
        'Packaging Specification.L': 'Packaging Dimension:Box 1: 69"x 42"x 6"x 87lbs\nBox 2,3,4,5,6,7,8,9: 39"L x 26"W x 7"H x 25 lbs ',
        'Packaging Specification.W': nan, 
        'Packaging Specification.H': nan, 
        'Package Dims': nan,
        'Total weight': 94,
        'cost': 451.67999999999995,
        'shippingCost': 125.19,
        'MAP': 587,
        'Description': "Riley", 
        'Features': 'Used as bar',
        'Specifications': nan, 
        'Country of origin': 'Vietnam', 
        'Shipping': 'Ground',
        'Image 1': 'https://www.dropbox.com/s/zvusucbvmbw4e96/V817SET3.jpg?dl=0', 
        'Image 2': 'https://www.dropbox.com/s/x1f2usmno58yalw/V817SET3_1.jpg?dl=0',
        'Image 3': 'https://www.dropbox.com/s/2dhftijrte2go5n/V817SET3_2.jpg?dl=0',
        'Image 4': 'https://www.dropbox.com/s/69o940of8j1ww2r/V817_dim.jpg?dl=0',
        'Image 5': 'https://www.dropbox.com/s/j8gfum1ka7vw9qy/V814_dim.jpg?dl=0',
    }
    result = VifahProductManager.parse_weight_info(data)
    assert len(result) > 0


def test_fetch_single_row(product_dao: ProductDao, brand_data: BrandData):
    brand_data.brandName = "Vifah"
    wpm = VifahProductManager(
        product_dao,
        brand_data,
        product_path, 
        outdoor_path, 
        office_path, 
        inventory_path, 
        sku_prefix=sku_prefix
    )
    df = pd.read_excel(product_path, skiprows=1)
    sku = list(df['SKU'])[0]
    default_id = f"{sku_prefix}-{sku}"
    assert_sku_fetch(wpm, default_id)

