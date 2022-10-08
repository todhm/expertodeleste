from typing import List, Dict

import pandas as pd

from mongodao.mongo_dao import MongoDao
from models.product_data import ProductData, Sku
from data_types.shipping import FIXED
from dataparser.numbers import round_up_decimals

class IntuitiveDao(object):


    def __init__(self, mongo_dao: MongoDao, fname: str):

        self.mongo_dao = mongo_dao
        self.df: pd.DataFrame = pd.read_csv(fname)
        
    def create_new_weight_info(self):
        self.df = self.df.groupby(['ProductId']).apply(self.find_weight_group).dropna(
            subset=['Length [in]', 'Width [in]', 'Height [in]', 'Weight [lb]']
        ).reset_index(drop=True)
        self.df.to_csv("datacollections/intuitive/newdata.csv")


    def fetch_new_info(self):
        return self.df.to_dict("records")

    def find_weight(self, data: pd.Series, product_data: ProductData):
        data = data.to_dict()
        length, width, height, weight = data['Length [in]'], data['Width [in]'], data['Height [in]'], data['Weight [lb]']
        if not product_data:
            return length, width, height, weight
        if data['VariantId'] == '[0]':
            if product_data and product_data.weightInfo:
                weight_info = product_data.weightInfo
                if product_data.weightInfoList:
                    weight = sum([x.packageWeight for x in product_data.weightInfoList])
                elif weight_info and weight_info.packageWeight:
                    weight = weight_info.packageWeight
                else:
                    weight = weight_info.weight
                length = weight_info.packageLength if weight_info.packageLength else weight_info.length
                height = weight_info.packageHeight if weight_info.packageHeight else weight_info.height
                width = weight_info.packageWidth if weight_info.packageWidth else weight_info.width
        else:
            sku = data['SKU']
            matched_sku: List[Sku] = list(filter(lambda x: x.skuId== sku , product_data.skuList))
            if matched_sku and matched_sku[0].weightInfo:
                if matched_sku[0].weightInfoList:
                    weight = sum([x.packageWeight for x in matched_sku[0].weightInfoList])
                elif matched_sku[0].weightInfo.packageWeight:
                    weight = matched_sku[0].weightInfo.packageWeight
                else:
                    weight = matched_sku[0].weightInfo.weight
                weight_info = matched_sku[0].weightInfo
                length = weight_info.packageLength if weight_info.packageLength else weight_info.length
                height = weight_info.packageHeight if weight_info.packageHeight else weight_info.height
                width = weight_info.packageWidth if weight_info.packageWidth else weight_info.width
        if length == 0:
            length = None
        if width == 0:
            width = None
        if height == 0:
            height = None
        if weight == 0:
            weight = None
        return length, width, height, weight
    
    def find_weight_group(self, df: pd.DataFrame) -> pd.DataFrame:
        product_id = df['ProductId'].reset_index(drop=True)[0].replace("[", '').replace("]", '')
        product_info = self.mongo_dao.fetch_single_data(
            {'shopifyId': f"gid://shopify/Product/{product_id}"},
            {'weightInfo': True, "skuList": True, "_id": False, "deliveryDataList": True}
        )
        if product_info:
            product_data = ProductData(**product_info)
        else:
            product_data = None
        if not product_data:
            return df
        if product_data.deliveryDataList and product_data.deliveryDataList[0].deliveryType == FIXED and product_data.deliveryDataList[0].price > 0:
            product_data.deliveryDataList[0].price = round_up_decimals(product_data.deliveryDataList[0].price, 2)
            df['Custom Shipping'] = f'13505:{product_data.deliveryDataList[0].price}:{product_data.deliveryDataList[0].price}'
        df[['Length [in]', 'Width [in]', 'Height [in]', 'Weight [lb]']] = df.apply(
            lambda x: self.find_weight(x, product_data), axis=1, result_type='expand'
        )
        return df

