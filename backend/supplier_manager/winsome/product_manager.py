from typing import List, Dict, Optional
import logging
import traceback
import random
import re

import pandas as pd
import numpy as np
from data_types.ship_type import LTL, PARCEL, ShipTypeType

from models import product_data
from config import ProductionConfig
from dataparser.excel_data import check_field_exists
from data_types.shipping import FREIGHT
from supplier_manager.default_product_manager import DefaultProductManager
from shopify_dao.product import ProductDao
from errors.products import NoProductError
from dataparser.image import upload_urls_to_s3_list
from dataparser.numbers import round_up_decimals
from dataparser.tags import add_additional_tag_to_product


logger = logging.getLogger(__name__)


class WinsomeProductManager(DefaultProductManager):


    def __init__(
        self, 
        product_dao: ProductDao,
        brand_data: product_data.BrandData, 
        product_path: str,
        stock_path: str,
        sku_prefix: str = 'WS',
        start_index: int = 0
    ):
        self.sku_prefix = sku_prefix
        self.brand_data = brand_data
        self.product_dao = product_dao
        product_df: pd.DataFrame = pd.read_excel(product_path, header=2)
        product_df = product_df[product_df['Product Type'] == 'Dining'].reset_index(drop=True)
        stock_df: pd.DataFrame = pd.read_excel(stock_path, header=1).dropna(
            subset=['Item#']
        ).reset_index(drop=True)
        product_df['Item #'] = product_df['Item #'].apply(lambda x: str(x))
        product_df[(product_df['Product Type'] == "Dining") | (product_df['Product Type'] == "Snack Table")]
        stock_df['Item#'] = stock_df['Item#'].apply(lambda x: str(int(x)))
        self.product_df = product_df.set_index('Item #').join(stock_df.set_index('Item#')).reset_index().rename(
            columns={
                "index": "Item #",
                "Alt Image #2": "Alt Img #2",
                'Main Image ': "Main Image"
            }
        )
        self.product_df = self.product_df.fillna(np.nan).replace([np.nan], [None])
        self.product_df = self.product_df.sort_values(by=['Avail Qty'], ascending=False).reset_index(drop=True)
        self.feature_column_list: List[str] = [f'Features {i}' for i in range(1, 9)]
        self.dark_color_re = r"black|coffee|walnut"
        self.bright_color_re = r"light oak|white|natural|teak"

    async def fetch_all_product_data_list(self) -> List[product_data.ProductData]:
        product_list = []
        for _, df_group in self.product_df.groupby("Item #"):
            productrow = None
            stockrow = None
            for _, row in df_group.iterrows():
                data = row.to_dict()
                if check_field_exists(data.get("Categories")):
                    productrow = data
                else:
                    stockrow = data
            product_list.append(await self.create_product_data(productrow, stockrow))
        return product_list

    async def upsert_all_product_data(self):
        for productid, df_group in self.product_df.groupby("Item #"):
            productrow = None
            weight_row_list = []
            for _, row in df_group.iterrows():
                data = row.to_dict()
                if check_field_exists(data.get("Categories")):
                    productrow = data
                else:
                    weight_row_list.append(data)
            try:
                data = await self.create_product_data(productrow, weight_row_list)
                if not data:
                    continue
                print(data.productId, "SUCCESS")
            except Exception as e:
                logger.error(f"Error while maake daata {str(e)} {productid}")
            try:
                if data.shopifyId:
                    self.product_dao.upsert_product(data, selected_keys=[
                        "variants",
                    ], update_meta=False)
                else:
                    self.product_dao.upsert_product(data)
            except Exception as e:
                logger.error(f"Error while upsert data {str(e)} {data.productId}")

    def parse_warranty(self) -> str:
        return self.brand_data.warranty

    def parse_shiptype_data(self, weight_info_list: List[product_data.WeightInfo]) -> ShipTypeType:
        weight_sum = sum([x.packageWeight for x in weight_info_list])
        if weight_sum >= 100:
            return LTL
        else:
            return PARCEL

    def fetch_single_row(self, sku_id: str) -> Dict:
        row = self.product_df[self.product_df['Item #'].apply(lambda x: f"{self.sku_prefix}-{x}") == sku_id]
        return row.to_dict('records')[0]

    async def create_product_data(self, x: Dict, weight_row_list: List= []) -> Optional[product_data.ProductData]:  
        default_id = f"{self.sku_prefix}-{x['Item #']}"
        try:
            product_model = self.product_dao.fetch_product(default_id)
            product_model.stock = self.parse_inventory_stock(x)
            product_model.price = self.make_price(x)
            product_model.cost = x['US $']
            product_model.upcCode=x['UPC']
            return product_model
        except NoProductError:
            pass
        try:
            tag =  x['tags'] if x.get('tags') else ''
            description_list = x.get("Long Description", "").split('\n')
            description_list = [x for x in description_list if x.strip()]
            description = description_list[0]
            product_model = product_data.ProductData(
                productId=default_id,
                cost=x['US $'],
                shortDescription=description,
                tagList=[y.strip() for y in tag.split(',') if y],
                productType='Kitchen & Dining Furniture Sets',
                trackInventory=True,
                brandName=self.brand_data.brandName,
                brandData=self.brand_data,
                upcCode=x['UPC'],
                taxable=True,
            )
            product_model.price = self.make_price(x)
            before_sale_price  = random.choice([100, 270, 330, 300, 250, 500, 300, 200, 400, 450]) + product_model.price
            product_model.beforeSalePrice = before_sale_price + product_model.price
            if check_field_exists(x['Video']):
                product_model.videoUrlList= [self.parse_video(x['Video'])]

        except Exception as e:
            logger.error(f"Error while make base product data {str(e)}")
            return None

        try:
            product_model.goodsName = self.parse_title(x)
        except Exception:
            logger.error(f"Error while make goods Name {product_model.productId}")
            return None

        try:
            product_model.mainImageList = await self.parse_main_image_list(default_id, x)
        except Exception:
            logger.error(f"Error while make main image list {product_model.productId} {traceback.format_exc()}")
            return None
        try:
            product_model.featureList = self.parse_feature_list(x)
        except Exception:
            logger.error(f"Error whlie make feature list {product_model.productId} {traceback.format_exc()}")
        try:
            product_model.description = self.make_product_description(product_model)
        except Exception:
            logger.error(f"Error while make description {product_model.productId} {traceback.format_exc()}")
            return None
        
        try:
            product_model.warranty = self.brand_data.warranty
        except Exception:
            logger.error(f"Error while make warranty {product_model.productId}")
            return None
        
        try:
            product_model.stock = self.parse_inventory_stock(x)
        except Exception as e:
            logger.error(f"Error while make stock {product_model.productId} {str(e)}")
            return None
        try:
            product_model.deliveryDataList = [self.parse_delivery_data()]
        except Exception:
            logger.error(f"Error while delivery data {product_model.productId}")
            return None
        try:
            self.parse_weight_info(x, product_model, weight_row_list)
        except Exception:
            logger.error(f"Error while make weight info data {product_model.productId} {traceback.format_exc()}")
            return None

        try:
            product_model.shipType = self.parse_shiptype_data(product_model.weightInfoList)
        except Exception:
            logger.error(f"Error while make weight info data {product_model.productId} {traceback.format_exc()}")
            return None
        try:
            product_model.goodsMustInfo = self.parse_must_info_list(x, weight_row_list)
        except Exception as e:
            logger.error(f"Error while make goodsmust info {product_model.productId} {str(e)}")
            return None
        try:
            product_model.warranty = self.brand_data.warranty
        except Exception:
            logger.error(f"Error while make warranty {product_model.productId}")
            return None
        
        try:
            product_model.productType = "Kitchen & Dining Furniture Sets"
            self.parse_tag_list(product_model, x)
            add_additional_tag_to_product(product_model)
        except Exception:
            logger.error(f"Error while make additional tags {product_model.productId} {traceback.format_exc()}")
            return None
        return product_model

    def parse_inventory_stock(self, x: Dict) -> int:
        if check_field_exists(x['Avail Qty']):
            return int(x['Avail Qty'])
        return 0

    def make_price(self, x: Dict) -> float:
        return round_up_decimals(x['US $'] * 1.25, decimals=0)
    
    def parse_title(self, x: Dict) -> str:
        name = x['Product Name']
        return f"Winsome {name}"

    def parse_video(self, x: Dict) -> str:
        name = x['Video']
        server_url = f"https://{ProductionConfig.BUCKET_NAME}.s3.{ProductionConfig.S3_REGION}.amazonaws.com/videos/{name}"
        return server_url
    
    # VPN없으면 작동안함
    async def parse_main_image_list(self, sku ,x: Dict) -> List[str]:
        image_array = []
        if check_field_exists(x['Main Image']):
            image_array.append(x['Main Image'])
        for i in range(1, 22):
            if check_field_exists(x[f'Alt Img #{i}']):
                image_array.append(x[f'Alt Img #{i}'])
        return await upload_urls_to_s3_list(image_array, f'/{sku}', quality=90, fix_image_width=775)

    def parse_delivery_data(self) -> product_data.DeliveryData:
        return product_data.DeliveryData(
            price=0,
            cost=0,
            deliveryType=FREIGHT,
            minDays=5,
            maxDays=10,
            freightDiscountRate=0.2
        )

    def parse_tag_list(self, product_model: product_data.ProductData, x: Dict) -> None:
        if check_field_exists(x['Color Finish']):
            color = x['Color Finish']
            if re.search(self.dark_color_re, color, flags=re.IGNORECASE):
                product_model.add_tag("Dark")
            elif re.search(self.bright_color_re, color, flags=re.IGNORECASE):
                product_model.add_tag("Bright")
        if not "Classics" in product_model.tagList or not "Modern" in product_model.tagList:
            product_model.add_tag("Simple")

    def add_product_mustinfo(self, x: Dict, must_info_list: List) -> product_data.MustInfo:
        product_type = None
        if check_field_exists(x['Bundle Part']):
            product_type = x['Bundle Part']
        elif check_field_exists(x['Categories']):
            product_type = x['Categories']
        if product_type:
            must_info_list.append(product_data.MustInfo(
                key=f"{product_type} Dimension(inches)",
                valueList=[
                    f"{x['Height']}Height x {x['Width']}Width x {x['Depth']}Depth"
                ],
            ))
            must_info_list.append(product_data.MustInfo(
                key=f"{product_type} Package Dimension(inches)",
                valueList=[
                    f"{x['Height.1']}Height x {x['Width.1']}Width x {x['Length']}Length"
                ],
            ))
            must_info_list.append(product_data.MustInfo(
                key=f"{product_type} Weight(lbs)",
                valueList=[
                    x['Weight']
                ],
            ))
            must_info_list.append(product_data.MustInfo(
                key=f"{product_type} Package Weight(lbs)",
                valueList=[
                    x['LBS']
                ],
            ))
        return must_info_list

    def parse_weight_info(self, x: Dict, product_model: product_data.ProductData, weight_row_list: List = []) -> None:
        weight_info =  product_data.WeightInfo(
            width=x['Width'],
            height=x['Height'],
            length=x['Depth'],
            weight=x['Weight'],
            packageWeight=x['LBS'],
            packageHeight=x['Height.1'],
            packageWidth=x['Width.1'],
            packageLength=x['Length'],
            cuft=x['CFT'],
        )
        product_model.weightInfo = weight_info
        additional_weight_info_list = []
        for weightrow in weight_row_list:
            additional_weight_info_list.append(product_data.WeightInfo(
                width=weightrow['Width'],
                height=weightrow['Height'],
                length=weightrow['Depth'],
                weight=weightrow['Weight'],
                packageWeight=weightrow['LBS'],
                packageHeight=weightrow['Height.1'],
                packageWidth=weightrow['Width.1'],
                packageLength=weightrow['Length'],
                cuft=weightrow['CFT'],
            ))
        additional_set_count = x['Total # of CTN']
        product_model.weightInfoList = [weight_info] + additional_weight_info_list
        if additional_set_count and len(product_model.weightInfoList) < additional_set_count:
            product_model.weightInfoList.append(
                product_model.weightInfoList[-1]
            )
        

    def parse_must_info_list(self, x:Dict, weight_info_list: List) -> List[product_data.MustInfo]:
        must_info_list = []
        if check_field_exists(x["Country Of Origin"]):
            must_info_list.append(product_data.MustInfo(
                key="Country Of Origin",
                valueList=[
                    str(x["Country Of Origin"])
                ],
            ))
        if check_field_exists(x["Color Finish"]):
            must_info_list.append(product_data.MustInfo(
                key="Finish Color",
                valueList=[
                    str(x["Color Finish"])
                ],
            ))
        if check_field_exists(x["Material"]):
            must_info_list.append(product_data.MustInfo(
                key="Material Detail",
                valueList=[
                    str(x["Material"])
                ],

            ))

        if check_field_exists(x["Table Shape"]):
            must_info_list.append(product_data.MustInfo(
                key="Table Shape",
                valueList=[
                    str(x["Table Shape"])
                ],

            ))
        if check_field_exists(x['Assembly']):
            must_info_list.append(product_data.MustInfo(
                key="Assembly Required",
                valueList=[
                    x['Assembly']
                ],

            ))
        self.add_product_mustinfo(x, must_info_list)
        for newrow in weight_info_list:
            self.add_product_mustinfo(newrow, must_info_list)
        return must_info_list

    def parse_feature_list(self, x: Dict) -> List[str]:
        description_list = x.get("Long Description", "").split('\n')
        description_list = [x for x in description_list if x.strip()]
        li_list = []
        for feature_col in self.feature_column_list:
            if check_field_exists(x[feature_col]):
                li_list.append(x[feature_col])
        for dimensioin in description_list[1:]:
            li_list.append(dimensioin)
        return li_list