import json

from shopify_dao.product import ProductDao
from dataparser.tags import add_additional_tag_to_product
from models.product_data import ProductData


def test_product_create(product_dao: ProductDao):
    with open('datacollections/HME3125.json', 'r') as f: 
        product_data = json.load(f)
        product_dao.db.product.insert_one(product_data)
    product_data = ProductData(**product_data)
    handle: str = product_data.productId
    result = product_dao.upsert_product(product_data)
    assert len(result.shopifyId) > 0
    assert len(result.skuList) >= 1
    data = product_dao.db.product.find_one({"productId": product_data.productId})
    new_product_data = product_dao.fetch_product(handle)
    assert len(data['shopifyId']) > 0
    assert len(data['skuList']) >= 1
    assert len(new_product_data.skuList) >= 1
    product_dao.delete_product(product_data.productId)



def test_upsert_inventory_goods(product_dao: ProductDao):
    with open('datacollections/productdata.json', 'r') as f: 
        product_data_list = json.load(f)
        product_data = list(filter(lambda x: x['productId'] == "AA891", product_data_list))[0]
        product_data['productType'] = 'Kitchen & Dining Furniture Sets'
        product_dao.db.product.insert_one(product_data)
    product_data = ProductData(**product_data)
    handle: str = product_data.productId
    new_product_data = product_dao.fetch_product(handle)
    result = product_dao.upsert_product(new_product_data)
    assert len(result.shopifyId) > 0
    data = product_dao.db.product.find_one({"productId": new_product_data.productId})
    assert len(data['shopifyId']) > 0


def test_review_existing_case(product_dao: ProductDao):
    with open('datacollections/productdata.json', 'r') as f: 
        product_data_list = json.load(f)
        product_data = list(filter(lambda x: x['productId'] == "LHD2246", product_data_list))[0]
        product_dao.db.product.insert_one(product_data)
    product_data = ProductData(**product_data)
    handle: str = product_data.productId
    new_product_data = product_dao.fetch_product(handle)
    result = product_dao.upsert_product(new_product_data)
    assert len(result.shopifyId) > 0
    data = product_dao.db.product.find_one({"productId": new_product_data.productId})
    assert len(data['shopifyId']) > 0



def test_product_update_with_new_tags(product_dao: ProductDao):
    with open('datacollections/productdata.json', 'r') as f: 
        product_data_list = json.load(f)
        product_data = list(filter(lambda x: x['productId'] == "LHD2246", product_data_list))[0]
        product_data['productType'] = 'Kitchen & Dining Furniture Sets'
        product_dao.db.product.insert_one(product_data)
    product_data = ProductData(**product_data)
    handle: str = product_data.productId
    new_product_data = product_dao.fetch_product(handle)
    new_product_data.tagList = [
        "Dining Sets",
        "Breakfast Nook",
        "Bright",
        "Big",
    ]
    result = product_dao.upsert_product(new_product_data, selected_keys=["tags"])
    assert len(result.shopifyId) > 0
    data = product_dao.db.product.find_one({"productId": new_product_data.productId})
    assert len(data['shopifyId']) > 0
    assert data['tagList'] == new_product_data.tagList

def test_product_tag_update_after_tag_updates(product_dao: ProductDao):
    with open('datacollections/productdata.json', 'r') as f: 
        product_data_list = json.load(f)
        product_data = list(filter(lambda x: x['productId'] == "CTY1666", product_data_list))[0]
        product_dao.db.product.insert_one(product_data)
    product_data = ProductData(**product_data)
    handle: str = product_data.productId
    new_product_data = product_dao.fetch_product(handle)
    add_additional_tag_to_product(new_product_data)
    result = product_dao.upsert_product(new_product_data, selected_keys=["tags"])
    assert len(result.shopifyId) > 0
    data = product_dao.db.product.find_one({"productId": new_product_data.productId})
    assert len(data['shopifyId']) > 0
    assert data['tagList'] == new_product_data.tagList
    assert "Big" in new_product_data.tagList
    assert "4 Seats" in new_product_data.tagList


def test_fetch_first_variant(product_dao: ProductDao):
    result = product_dao.fetch_first_variant_id("011-744-011-636")
    assert result.isdigit()


def test_fetch_product_data(product_dao: ProductDao):
    pd = product_dao.fetch_product_data_from_shopify("cerave-resurfacing-retinol-serum")
    assert len(pd.shopifyId) > 0
    
