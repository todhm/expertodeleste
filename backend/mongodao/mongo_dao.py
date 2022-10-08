from typing import List, Dict
from pymongo.database import Database
from pymongo.database import Collection
from models.product_data import DefaultDataClass, ProductData


class MongoDao(object):


    def __init__(self, db: Database, col: str = "product"):
        self.db: Database = db
        self.col: Collection = self.db[col]


    def insert_data_list(self, data_list :List[DefaultDataClass] = []):
        self.col.insert_many([x.to_json for x in data_list])

    def fetch_data(self, data_dict: Dict, fetch_dict: Dict = {}) -> List[Dict]:
        return list(self.col.find(data_dict, fetch_dict))

    def fetch_product_list_data(self, data_dict: Dict) -> List[ProductData]:
        product_data_list = []
        for data in self.col.find(data_dict, {"_id": False}):
            product_data_list.append(ProductData(**data))
        return product_data_list

    def fetch_single_data(self, data_dict: Dict, fetch_dict: Dict = {}) -> List[Dict]:
        return self.col.find_one(data_dict, fetch_dict)

    def upsert_mongo_product_data(self, product_data: ProductData, selected_mongo_fields: List[str] = []) -> None:
        update_mongo_data = product_data.to_json
        if selected_mongo_fields:
            new_mongo_dict = {}
            for key in selected_mongo_fields:
                new_mongo_dict[key] = update_mongo_data[key]
            update_mongo_data = new_mongo_dict
        self.db.product.update_one({
            "productId": product_data.productId
        }, {"$set": update_mongo_data}, upsert=True)

    def delete_many_query(self, query: Dict) -> None:
        self.col.delete_many(query)


