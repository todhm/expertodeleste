from typing import List, Dict, Optional
import logging
import traceback
import random
import re

import pandas as pd
import numpy as np
import data_types
from data_types.ship_type import LTL, PARCEL, ShipTypeType
from dataparser.numbers import round_up_decimals

from models import product_data
from dataparser.excel_data import check_field_exists
from data_types.shipping import FIXED
from supplier_manager.default_product_manager import DefaultProductManager
from shopify_dao.product import ProductDao
from errors.products import NoProductError
from dataparser.image import upload_urls_to_s3_list
from dataparser.tags import add_additional_tag_to_product
from dataparser.strings import parse_specification_string
from data_types import tag_types


logger = logging.getLogger(__name__)


class ArtProductManager(DefaultProductManager):


    def __init__(
        self, 
        product_dao: ProductDao,
        brand_data: product_data.BrandData, 
        product_path: str,
        stock_path: str,
        sku_prefix: str = 'ART',
        start_index: int = 0
    ):
        self.sku_prefix = sku_prefix
        self.brand_data = brand_data
        self.product_dao = product_dao
        df: pd.DataFrame = pd.read_excel(product_path)
        stock_df: pd.DataFrame = pd.read_excel(stock_path)
        df['product'] = df['product'].apply(lambda x: x.strip())
        stock_df['Product'] = stock_df['Product'].apply(lambda x: x.strip())
        df = df.rename(
            columns=lambda x: x.strip().replace("\n", ' ').replace("\t", ' ').replace("  ", ' ')
        )
        self.df: pd.DataFrame = df.set_index('product').join(stock_df.set_index('Product')).reset_index()
        self.df = self.df.rename(
            columns=lambda x: x.strip().replace("\n", ' ').replace("\t", ' ').replace("  ", ' ')
        )
        self.df = self.df.fillna(np.nan).replace([np.nan], [None])
        self.product_df: pd.DataFrame = self.df[
            (self.df['type'].str.match(f"{self.dining_match_re}|{self.coocktail_table_re}", case=False, na=False))
            |(self.df['type'].str.match(self.dining_chair_match_re, case=False, na=False))
            |(self.df['type'].str.match(self.dining_buffet_match_re, case=False, na=False))
        ]
        self.product_df = self.product_df[
            self.product_df['product'].apply(lambda x: x.replace('-', '').isdigit())
        ]
        self.product_df = self.product_df.dropna(subset=['Primary image URL'])
        self.product_df = self.product_df[start_index:].reset_index(drop=True)

    async def fetch_all_product_data_list(self) -> List[product_data.ProductData]:
        product_list = []
        for _, data in self.product_df.iterrows():
            product_list.append(await self.create_product_data(data.to_dict()))
        return product_list

    async def upsert_all_product_data(self):
        for _, row in self.product_df.iterrows():
            try:
                row = row.to_dict()
                default_id = row['product']
                additional_rows = self.df[self.df['product'].apply(lambda x: x in 
                [f'{default_id}TP', f'{default_id}BS'])].to_dict('records')
                data = await self.create_product_data(row, additional_rows)
                print(data.productId, "SUCCESS")
            except Exception as e:
                logger.error(f"Error while make daata {str(e)} {default_id}")
                continue
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
        if weight_sum >= 50:
            return LTL
        else:
            return PARCEL

    def fetch_single_row(self, sku_id: str) -> Dict:
        row = self.product_df[self.product_df['product'].apply(lambda x: f"{self.sku_prefix}-{x}") == sku_id]
        return row.to_dict('records')[0]

    async def create_product_data(self, x: Dict, additional_row_list: List= []) -> Optional[product_data.ProductData]:  
        default_id = f"{self.sku_prefix}-{x['product']}"
        try:
            product_model = self.product_dao.fetch_product(default_id)
            product_model.stock = self.parse_inventory_stock(x)
            product_model.price = self.make_price(x)
            product_model.cost = float(x['Price'])
            return product_model
        except NoProductError:
            pass
        try:
            tag =  x['tags'] if x.get('tags') else ''
            product_model = product_data.ProductData(
                productId=default_id,
                tagList=[y.strip() for y in tag.split(',') if y],
                productType='Kitchen & Dining Furniture Sets',
                trackInventory=True,
                brandName=self.brand_data.brandName,
                brandData=self.brand_data,
                taxable=True,
                cost=float(x['Price']),
                upcCode=x.get('upc', '')
            )
            product_model.price = self.make_price(x)
            before_sale_price  = random.choice([100, 270, 330, 300, 250, 500, 300, 200, 400, 450]) + product_model.price
            product_model.beforeSalePrice = before_sale_price + product_model.price
        except Exception as e:
            raise ValueError(f"Error while make base product data {default_id} {traceback.format_exc()}")

        try:
            product_model.goodsName = self.parse_title(x)
        except Exception:
            message = f"Error while make goods Name {product_model.productId}"
            raise ValueError(message)

        try:
            product_model.mainImageList = await self.parse_main_image_list(default_id, x)
        except Exception:
            raise ValueError(f"Error while make main image list {product_model.productId} {traceback.format_exc()}")
        try:
            product_model.featureList = self.parse_feature_list(x)
        except Exception:
            raise ValueError(f"Error whlie make feature list {product_model.productId} {traceback.format_exc()}")
        try:
            product_model.shortDescription = self.parse_short_description(x, additional_row_list=additional_row_list)
        except Exception:
            raise ValueError(f"Error while make short description {product_model.productId}")
        try:
            product_model.description = self.make_product_description(product_model)
        except Exception:
            raise ValueError(f"Error while make description {product_model.productId} {traceback.format_exc()}")
        
        try:
            product_model.warranty = self.brand_data.warranty
        except Exception:
            raise ValueError(f"Error while make warranty {product_model.productId}")
        
        try:
            product_model.stock = self.parse_inventory_stock(x)
        except Exception as e:
            raise ValueError(f"Error while make stock {product_model.productId} {str(e)}")

        try:
            product_model.deliveryDataList = [self.parse_delivery_data()]
        except Exception:
            raise ValueError(f"Error while delivery data {product_model.productId}")
        try:
            self.parse_weight_info(x, product_model, additional_row_list)
        except Exception:
            raise ValueError(f"Error while make weight info data {product_model.productId} {traceback.format_exc()}")

        try:
            product_model.shipType = self.parse_shiptype_data(product_model.weightInfoList)
        except Exception:
            raise ValueError(f"Error while make weight info data {product_model.productId} {traceback.format_exc()}")
        try:
            product_model.goodsMustInfo = self.parse_must_info_list(x)
        except Exception as e:
            raise ValueError(f"Error while make goodsmust info {product_model.productId} {str(e)}")

        try:
            product_model.warranty = self.brand_data.warranty
        except Exception:
            raise ValueError(f"Error while make warranty {product_model.productId}")

        
        try:
            product_model.productType = "Kitchen & Dining Furniture Sets"
            self.parse_tag_list(product_model, x)
            add_additional_tag_to_product(product_model)
        except Exception:
            raise ValueError(f"Error while make additional tags {product_model.productId} {traceback.format_exc()}")
        return product_model

    def parse_inventory_stock(self, x: Dict) -> int:
        if check_field_exists(x['Available']):
            return int(x['Available'])
        return 0

    def make_price(self, x: Dict) -> float:
        if check_field_exists(x['IMAP Price']):
            return float(x['IMAP Price'])
        else:
            return round_up_decimals(x['Price'] * 1.8, decimals=-1)
    
    def make_cost(self, x: Dict) -> float:
        return float(x['Price'])
    
    def parse_title(self, x: Dict) -> str:
        name = x['name']
        return f"A.R.T. Furniture {name}"
    
    # VPN없으면 작동안함
    async def parse_main_image_list(self, sku ,x: Dict) -> List[str]:
        image_array = []
        for i in range(1, 11):
            if check_field_exists(x[f'Image {i} Url']):
                image_array.append(x[f'Image {i} Url'].strip())
        if not image_array:
            image_array.append(x['Primary image URL'].strip())
        return await upload_urls_to_s3_list(
            image_array, f'/{self.sku_prefix}/{sku}/', quality=90, fix_image_width=775
        )

    def parse_delivery_data(self) -> product_data.DeliveryData:
        return product_data.DeliveryData(
            price=0,
            cost=0,
            deliveryType=FIXED,
            minDays=5,
            maxDays=10,
        )

    def parse_tag_list(self, product_model: product_data.ProductData, x: Dict) -> None:
        if check_field_exists(x['family']):
            family = x['family']
            if re.search('transitional|tranditional|english', family, flags=re.IGNORECASE):
                product_model.add_tag(tag_types.CLASSICS)
            else:
                product_model.add_tag(tag_types.MODERN)
            if re.search(self.dining_chair_match_re, family, flags=re.IGNORECASE):
                product_model.add_tag(tag_types.DINING_CHAIR)
                product_model.add_tag(tag_types.NONE_TABLE)
            if re.search(self.dining_buffet_match_re, family, flags=re.IGNORECASE):
                product_model.add_tag(tag_types.NONE_TABLE)
                product_model.add_tag(tag_types.DINING_BUFFET)
            
        if check_field_exists(x['Detail Finish']):
            color = x['Detail Finish']
            if re.search(self.dark_color_re, color, flags=re.IGNORECASE):
                product_model.add_tag(tag_types.DARK)
            elif re.search(self.bright_color_re, color, flags=re.IGNORECASE):
                product_model.add_tag(tag_types.BRIGHT)
    
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
    
    def parse_single_row_weight(self, x: Dict) -> product_data.WeightInfo:
        weight_info =  product_data.WeightInfo(
            packageWidth=float(x['dim_width']),
            packageHeight=float(x['dim_height']),
            packageLength=float(x['dim_depth']),
            packageWeight=float(x['weight'])
        )
        weight_info.cuft = float(x['volume'])
        width, height, length, _ = parse_specification_string(x['Product Dimensions (in)'])
        weight_info.width = width
        weight_info.height = height
        weight_info.length = length
        if weight_info.packageWidth == 0:
            weight_info.packageWidth = weight_info.width
            weight_info.packageHeight = weight_info.height
            weight_info.packageLength = weight_info.length
        return weight_info

    def parse_weight_info(self, x: Dict, product_model: product_data.ProductData, additional_row_list: List = []) -> None:
        if not additional_row_list:
            weight_info = self.parse_single_row_weight(x)
            product_model.weightInfo = weight_info
            product_model.weightInfoList = [weight_info]
            return
        weight_info_list = []
        for row in additional_row_list:
            weight_info_list.append(self.parse_single_row_weight(row))
        product_model.weightInfo = weight_info_list[0]
        product_model.weightInfoList = weight_info_list

    def parse_must_info_list(self, x:Dict) -> List[product_data.MustInfo]:
        must_info_list = []
        if check_field_exists(x["Detail Finish"]):
            must_info_list.append(product_data.MustInfo(
                key="Detail Finish",
                valueList=[
                    str(x["Detail Finish"])
                ],
            ))
        if check_field_exists(x["family"]):
            must_info_list.append(product_data.MustInfo(
                key="Family",
                valueList=[
                    str(x["family"])
                ],

            ))
        if check_field_exists(x["Product Dimensions (in)"]):
            must_info_list.append(product_data.MustInfo(
                key="Product Dimensions (in)",
                valueList=[
                    str(x["Product Dimensions (in)"])
                ],
            ))
        if check_field_exists(x["Carton Dimensions (in)"]):
            must_info_list.append(product_data.MustInfo(
                key="Carton Dimensions (in)",
                valueList=[
                    str(x["Carton Dimensions (in)"])
                ],
            ))
        if check_field_exists(x["Materials"]):
            must_info_list.append(product_data.MustInfo(
                key="Material Detail",
                valueList=[
                    str(x["Materials"])
                ],
            ))
        if check_field_exists(x["type"]):
            must_info_list.append(product_data.MustInfo(
                key="Product Type",
                valueList=[
                    str(x["type"])
                ],
            ))
        return must_info_list

    def parse_feature_list(self, x: Dict) -> List[str]:
        if check_field_exists(x['Features']):
            feature_list = x.get("Features", "").split('</br>')
            feature_list = [x for x in feature_list if x.strip()]
            if len(feature_list) > 1:
                return feature_list
        if check_field_exists(x['Materials']):
            feature_list = x.get("Materials", '').split(",")
            return feature_list
        return []

    def parse_short_description(sseslf, x: Dict, additional_row_list: List[Dict]) -> str:
        if check_field_exists(x['Product Overview']):
            return x['Product Overview']
        if additional_row_list:
            description = ' '.join([x['Product Overview'] for x in additional_row_list if check_field_exists(['Product Overview'])])
            if description:
                split_by_sentence = description.split('.')
                res = []
                [res.append(x) for x in split_by_sentence if x not in res]
                return '.'.join(res)
            return x['description']
            