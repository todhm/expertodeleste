from typing import Dict
import pandas as pd
from mongodao.mongo_dao import MongoDao
from supplier_manager.acme.product_manager import AcmeProductManager
from models.product_data import ProductData, WeightInfo, Sku
from intuitive_dao.intuitive_dao import IntuitiveDao
from random import randint


def insert_test_intuitive_data(df: pd.DataFrame) -> ProductData:
    product_id = df['ProductId'].reset_index(drop=True)[0].replace("[", '').replace("]", '')
    shopify_id = f"gid://shopify/Product/{product_id}"
    product_data = ProductData(
        shopifyId=shopify_id
    )
    weight_info = WeightInfo(
        weight=randint(40, 300),
        width=randint(40, 50),
        length=randint(40, 50),
        height=randint(40, 50),
        packageWeight=randint(40, 50),
        packageHeight=randint(40, 50),
        packageLength=randint(40, 50),
        packageWidth=randint(40, 50),
    )
    product_data.weightInfo = weight_info
    if df['VariantId'].reset_index(drop=True)[0] == '[0]':
        product_data.productId =  df['SKU'].reset_index(drop=True)[0]
    else:
        sku_list = []
        for idx, data in df.iterrows():
            weight_info = WeightInfo(
                weight=randint(40, 300),
                width=randint(40, 50),
                length=randint(40, 50),
                height=randint(40, 50),
                packageWeight=randint(40, 50),
                packageHeight=randint(40, 50),
                packageLength=randint(40, 50),
                packageWidth=randint(40, 50),
            )
            sku = Sku(
                skuId=data['SKU'],
            )
            sku.weightInfo = weight_info
            sku_list.append(sku)
            
        product_data.skuList = sku_list
    return product_data


def test_intuitive_dao(mongodb):
    # Mongo db에 Acme Product Data가 존재하고 이를매치해서 weight정보를 업데이트시킨다.
    
    mongo_dao = MongoDao(mongodb)
    df = pd.read_csv("datacollections/intuitive/test.csv")
    insert_df = df.groupby(["ProductId"]).apply(insert_test_intuitive_data)
    mongo_dao.insert_data_list(list(insert_df))
    in_dao = IntuitiveDao(mongo_dao, "datacollections/intuitive/test.csv")
    in_dao.create_new_weight_info()
    new_data_list = in_dao.fetch_new_info()
    assert len(new_data_list) > 0
    for x in new_data_list:
        assert x['Length [in]'] > 0
        assert x['Width [in]'] > 0
        assert x['Height [in]'] > 0
        assert x['Weight [lb]'] > 0
    newdf = pd.read_csv("datacollections/intuitive/newdata.csv")
    assert len(newdf) > 0
