import json
from typing import List, Generator

import shopify
from shopify.resources.shop import Shop
from pymongo.database import Database
from typing import Dict, Optional

from shopify_dao.inventory import InventoryDao
from models import product_data as pd
from graphqlqueries.product import (
    shopify_product_query,
    create_product_query,
    update_product_query,
    delete_product_query,
    shopify_get_first_variant,
    UPDATE_METAFIELD_QUERIES
)
from dataparser import product
from errors.products import NoProductError
from mongodao.mongo_dao import MongoDao

class ProductDao(object):


    def __init__(self, shop: Shop, db: Database):
        self.shop = shop
        self.db = db
        self.mongo_dao: MongoDao = MongoDao(db, 'product')
        self._inventory_id = None

    @property
    def inventory_id(self):
        if not self._inventory_id:
            inventory_dao = InventoryDao(self.shop, self.db)
            self._inventory_id = inventory_dao.fetch_default_inventory_id()
        return self._inventory_id


    # https://shopify.dev/api/admin-graphql/2022-04/input-objects/MetafieldsSetInput 참조
    # https://locamusica.myshopify.com/admin/metafields/product
    def update_metafields(self, 
        product_data: pd.ProductData,
        key_list: List[str] = [],
        update_mongo: bool = False,
        mongo_key_list: List[str] = [],
    ):
        review_point = product.calculate_review_average(product_data)
        metafields = {
            "metafields": [
            {
                "type": "json",
                "ownerId": product_data.shopifyId,
                "namespace": "my_fields",
                "key": "mustinfo",
                "value": json.dumps([x.to_json for x in product_data.goodsMustInfo]),
            },
            {
                "type": "json",
                "ownerId": product_data.shopifyId,
                "namespace": "my_fields",
                "key": "defaultsetlist",
                "value": json.dumps([x.to_json for x in product_data.defaultSetList])
            },
            {
                "type": "json",
                "ownerId": product_data.shopifyId,
                "namespace": "my_fields",
                "key": "additionalproductlist",
                "value": json.dumps([x.to_json for x in product_data.additionalProductList])
            },
            {
                "type": "number_decimal",
                "ownerId": product_data.shopifyId,
                "namespace": "reviews",
                "key": "averageRating",
                "value": str(review_point)
            },
            {
                "type": "number_integer",
                "ownerId": product_data.shopifyId,
                "namespace": "reviews",
                "key": "rating_count",
                "value": str(len(product_data.reviewList))
            },
        ]}
        if product_data.brandData:
            metafields['metafields'].append({
                "type": "json",
                "ownerId": product_data.shopifyId,
                "namespace": "my_fields",
                "key": "branddata",
                "value": json.dumps(product_data.brandData.to_json)
            })
        if product_data.warranty:
            metafields['metafields'].append({
                "type": "multi_line_text_field",
                "ownerId": product_data.shopifyId,
                "namespace": "my_fields",
                "key": "warranty",
                "value": product_data.warranty
            })
        if product_data.manual:
            metafields['metafields'].append({
                "type": "multi_line_text_field",
                "ownerId": product_data.shopifyId,
                "namespace": "custom",
                "key": "manual",
                "value": product_data.manual
            })
        if product_data.ingredient:
            metafields['metafields'].append({
                "type": "multi_line_text_field",
                "ownerId": product_data.shopifyId,
                "namespace": "custom",
                "key": "ingredient",
                "value": product_data.ingredient
            })
        if product_data.description:
            metafields['metafields'].append({
                "type": "multi_line_text_field",
                "ownerId": product_data.shopifyId,
                "namespace": "custom",
                "key": "description",
                "value": product_data.description
            })
        if product_data.deliveryDataList:
            metafields['metafields'].append({
                "type": "number_integer",
                "ownerId": product_data.shopifyId,
                "namespace": "my_fields",
                "key": "min_delivery_days",
                "value": str(product_data.deliveryDataList[0].minDays)
            })
            metafields['metafields'].append({
                "type": "number_integer",
                "ownerId": product_data.shopifyId,
                "namespace": "my_fields",
                "key": "max_delivery_days",
                "value": str(product_data.deliveryDataList[0].maxDays)
            })
            metafields['metafields'].append({
                "type": "number_decimal",
                "ownerId": product_data.shopifyId,
                "namespace": "my_fields",
                "key": "shipping_price",
                "value": str(product_data.deliveryDataList[0].price)
            })
            metafields['metafields'].append({
                "type": "single_line_text_field",
                "ownerId": product_data.shopifyId,
                "namespace": "my_fields",
                "key": "shipping_type",
                "value": product_data.deliveryDataList[0].deliveryType
            })
            metafields['metafields'].append({
                "type": "number_decimal",
                "ownerId": product_data.shopifyId,
                "namespace": "my_fields",
                "key": "freight_discount_rate",
                "value": str(product_data.deliveryDataList[0].freightDiscountRate)
            })
        if key_list:
            metafields['metafields'] = list(filter(lambda x: x['key'] in key_list, metafields['metafields']))
        result = json.loads(shopify.GraphQL().execute(UPDATE_METAFIELD_QUERIES, variables=metafields))
        if result.get('errors'):
            raise ValueError(result)
        data = result['data']["metafieldsSet"]
        if data.get("userErrors"):
            raise ValueError(data.get("userErrors"))
        if update_mongo:
            self.mongo_dao.upsert_mongo_product_data(product_data, selected_mongo_fields=mongo_key_list)
        return data

    def call_shopify_data(self, graphql_query: str, upsert_dict: Dict, data_key: str) -> Dict:
        result = shopify.GraphQL().execute(graphql_query, variables={"input": upsert_dict})
        result_json = json.loads(result)
        if result_json.get('errors'):
            raise ValueError(result_json)
        if result_json.get("data", {}).get(data_key, {}).get("userErrors", []):
            raise ValueError(result_json.get("data", {}).get(data_key, {}).get("userErrors", []))
        if not result_json.get("data", {}).get(data_key):
            raise ValueError(result_json)
        return result_json

    def update_shopify_data(self, product_data: pd.ProductData) -> None:
        upsert_dict = product.product_data_to_shopify_format(product_data, self.inventory_id)
        graphql_query = update_product_query()
        data_key = "productUpdate"
        _ = self.call_shopify_data(graphql_query, upsert_dict, data_key)
        self.update_metafields(product_data)

    def upsert_product(
        self, 
        product_data: pd.ProductData, 
        selected_keys: List[str] = [],
        selected_mongo_fields: List[str] = [],
        update_mongo: bool = True, 
        update_meta: bool = True,
    ) -> pd.ProductData:
        if not product_data.shopifyId:
            product_dict = self.db.product.find_one({"productId": product_data.productId}, {"shopifyId": 1})
            if product_dict:
                product_data.shopifyId = product_dict.get('shopifyId')
        upsert_dict = product.product_data_to_shopify_format(product_data, self.inventory_id)
        if product_data.shopifyId:
            graphql_query = update_product_query()
            data_key = "productUpdate"
        else:
            graphql_query = create_product_query()
            data_key = "productCreate"
        if selected_keys:
            new_upsert_dict = {}
            new_upsert_dict['id'] = product_data.shopifyId
            for key in selected_keys:
                new_upsert_dict[key] = upsert_dict[key]
            upsert_dict = new_upsert_dict
        result_json = self.call_shopify_data(graphql_query, upsert_dict, data_key)
        shopify_id = result_json['data'][data_key]['product']['id']
        product_data.shopifyId = shopify_id
        if update_mongo:
            self.mongo_dao.upsert_mongo_product_data(product_data, selected_mongo_fields=selected_mongo_fields)
        if update_meta:
            self.update_metafields(product_data)
        return product_data

    def fetch_product_id(self, handle: str) -> str:
        query = shopify_product_query(handle)
        result = shopify.GraphQL().execute(query)
        result_json = json.loads(result)
        result = result_json['data']['productByHandle']
        if not result:
            raise ValueError("No results")
        return result['id']

    def fetch_product_data_from_shopify(self, handle: str) -> pd.ProductData:
        query = shopify_product_query(handle)
        result = shopify.GraphQL().execute(query)
        result_json = json.loads(result)
        result = result_json['data']['productByHandle']
        product_data = product.shopify_data_to_product_data(result)
        return product_data

    def fetch_all_products(self, query: Optional[Dict] = {}) -> Generator[pd.ProductData, None, None]:
        for product in self.db.product.find(query,{"_id": False}):
            yield pd.ProductData(**product)

    def fetch_first_variant_id(self, handle:str) -> str:
        query = shopify_get_first_variant(handle.lower())
        result = shopify.GraphQL().execute(query)
        result_json = json.loads(result)
        variant_id = result_json['data']['productByHandle']['variants']['edges'][0]['node']['id']
        return variant_id.split("/ProductVariant/")[1]

    def delete_product(self, handle: str) -> None:
        product_data = self.db.product.find_one({"productId": handle}, {"shopifyId": True})
        if not product_data or not product_data.get("shopifyId"):
            raise NoProductError("No product exists on MongoDB")
        query = delete_product_query()
        _ = self.call_shopify_data(query, {"id": product_data['shopifyId']}, "productDelete")
        return True


    def fetch_product(self, handle: str) -> pd.ProductData:
        product_data = self.db.product.find_one({"productId": handle})
        if not product_data:
            raise NoProductError("No product exists on MongoDB")
        product_data = pd.ProductData(**product_data)
        return product_data