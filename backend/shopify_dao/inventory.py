import json
from typing import Dict

import shopify
from shopify.resources.shop import Shop
from pymongo.database import Database

from graphqlqueries.inventory import INVENTORY_FETCH_QUERIES


class InventoryDao(object):


    def __init__(self, shop: Shop, db: Database):
        self.shop = shop
        self.db = db


    def fetch_inventory_map(self) -> Dict:
        result = shopify.GraphQL().execute(INVENTORY_FETCH_QUERIES)
        result = json.loads(result)
        data_map = {}
        for node in result.get("data", {}).get("shop", {}).get('locations', {}).get('edges', []):
            node_data = node['node']
            data_map[node_data['name']] = node_data['id']
        return data_map

    def fetch_default_inventory_id(self) -> str:
        result = shopify.GraphQL().execute(INVENTORY_FETCH_QUERIES)
        result = json.loads(result)
        for node in result.get("data", {}).get("shop", {}).get('locations', {}).get('edges', []):
            node_data = node['node']
            return node_data['id']