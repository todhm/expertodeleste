import json
from typing import Dict

import shopify
from shopify.resources import graphql
from shopify.resources.shop import Shop
from pymongo.database import Database

from graphqlqueries.publication import PUBLICATION_QUERY

class PublicationDao(object):


    def __init__(self, shop: Shop, db: Database):
        self.shop = shop
        self.db = db


    def update_publication(self, shopify_id: str) -> bool:
        query = {

        }
        result = shopify.GraphQL().execute(PUBLICATION_QUERY, {})
        result = json.loads(result)
        data_map = {}
        for node in result.get("data", {}).get("shop", {}).get('locations', {}).get('edges', []):
            node_data = node['node']
            data_map[node_data['name']] = node_data['id']
        return data_map