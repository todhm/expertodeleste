from typing import List, Dict, Optional
import logging
import traceback
import time

import pandas as pd
import numpy as np

from models import product_data
from dataparser.excel_data import check_field_exists
from data_types.shipping import FREIGHT
from data_types.ship_type import ShipTypeType, LTL, PARCEL
from supplier_manager.default_product_manager import DefaultProductManager
from shopify_dao.product import ProductDao
from errors.products import NoProductError
from dataparser.image import upload_url_to_s3, upload_urls_to_s3_list
from dataparser.numbers import round_up_decimals
from dataparser.tags import add_additional_tag_to_product


logger = logging.getLogger(__name__)


class AcmeProductManager(DefaultProductManager):


    def __init__(
        self, 
        product_dao: ProductDao,
        brand_data: product_data.BrandData, 
        product_path: str,
        image_path: str,
        price_path: str,
        sku_prefix: str = 'ACME',
        start_index: int = 0
    ):
        self.sku_prefix = sku_prefix
        self.brand_data = brand_data
        self.product_dao = product_dao
        product_df: pd.DataFrame = pd.read_csv(product_path)
        product_df = product_df[start_index:].reset_index(drop=True)
        product_df['acme.sku'] = product_df['acme.sku'].apply(lambda x: str(x))
        image_df: pd.DataFrame = pd.read_csv(image_path)
        image_df['acme.sku'] = image_df['acme.sku'].apply(lambda x: str(x))
        price_df: pd.DataFrame = pd.read_csv(price_path)
        price_df['catalog_product_attribute.sku'] = price_df['catalog_product_attribute.sku'].apply(lambda x: str(x))
        self.product_df = product_df.set_index('acme.sku').join(image_df.set_index('acme.sku')).reset_index()
        self.product_df = self.product_df.set_index('acme.sku').join(price_df.set_index('catalog_product_attribute.sku')).reset_index()
        self.product_df = self.product_df.fillna(np.nan).replace([np.nan], [None])
        regex_match = r"((?=.*dining)(?=.*table))|((?=.*dining)(?=.*set))|((?=.*height)(?=.*table))|((?=.*patio)(?=.*set))|((?=.*bar)(?=.*set))|((?=.*counter)(?=.*height)(?=.*set))"
        temp_df_cond = self.product_df[
            self.product_df['acme.product_type'].str.match(regex_match, case=False, na=False)
        ]
        group_list = [x for x in list(temp_df_cond['acme.group']) if x ]
        self.dining_product_df = self.product_df[
            (self.product_df['acme.product_type'].str.match(regex_match, case=False, na=False))
            |
            (self.product_df['acme.group'].isin(group_list))
        ]

        
    async def fetch_all_product_data_list(self) -> List[product_data.ProductData]:
        product_list = []
        for _, row in self.dining_product_df.iterrows():
            product_list.append(await self.create_product_data(**row.to_dict()))
        return product_list
    
    def fetch_single_row(self, sku_id: str) -> Dict:
        sku_dict_list = self.product_df[self.product_df['acme.sku'].apply(lambda x: f"{self.sku_prefix}-{x}") == sku_id]
        return sku_dict_list.to_dict('records')[0]

    def parse_shiptype_data(self, x: Dict) -> ShipTypeType:
        if x['acme.ship_type'] == "LTL":
            return LTL
        else:
            return PARCEL

    def fetch_matched_additional_list(self, group_id: str, original_id: str) -> List[product_data.ProductData]:
        return self.product_df[
            (self.product_df['acme.sku'].apply(lambda x: f"{self.sku_prefix}-{x}") != original_id)
            & 
            (self.product_df['acme.group'] == group_id)
        ]

    async def upsert_all_acme_data(self):
        data_map = {}
        for _, row in self.dining_product_df.iterrows():
            try:
                data = await self.create_product_data(**row.to_dict())
                data_map[data.productId] = data
            except Exception as e:
                logger.error(f"Error while parsing data {str(e)}")
            try:
                self.product_dao.upsert_product(data)
                print("Upsert product", data.productId, data.shopifyId)
            except Exception as e:
                logger.error(f"Error while upsert data with shopify {str(e)}")

            if data and data.additionalProductList:
                matched_additioinal_product_list = []
                try:
                    added_df = self.fetch_matched_additional_list(data.additionalGroupId, data.productId)
                except Exception as e:
                    logger.error(f"Error while fetching additional data {str(e)}")
                    
                product_variant_map = {}
                for _, row in added_df.iterrows():
                    try:
                        row_dict = row.to_dict()
                        sku = f"{self.sku_prefix}-{row_dict['acme.sku']}"
                        if data_map.get(row_dict.get(sku)):
                            product_model = data_map[sku]
                        else:
                            product_model = await self.create_product_data(**row.to_dict())
                            data_map[data.productId] = product_model
                        if not product_model.shopifyId:
                            product_model = self.product_dao.upsert_product(product_model)
                        variant_id = self.product_dao.fetch_first_variant_id(product_model.productId)
                        product_variant_map[product_model.productId] = {
                            "variantId": variant_id,
                            "price": product_model.price, 
                            "beforeSalePrice": product_model.beforeSalePrice,
                            "isSoldOut": product_model.stock == 0
                        }
                    except Exception:
                        logger.error(f"Error whlie creating additional product map {data.productId}")
                        continue
                try:
                    for add_data in data.additionalProductList:
                        if product_variant_map.get(add_data.productId):
                            add_data.shopifyVariantId = product_variant_map[add_data.productId]['variantId']
                            add_data.price = product_variant_map[add_data.productId]['price']
                            add_data.beforeSalePrice = product_variant_map[add_data.productId]['beforeSalePrice']
                            add_data.isSoldOut = product_variant_map[add_data.productId]['isSoldOut']
                            matched_additioinal_product_list.append(add_data)
                    data.additionalProductList = matched_additioinal_product_list
                    self.product_dao.update_metafields(data, key_list=['additionalproductlist'], update_mongo=True)
                    print("Create additional id", data.productId, data.shopifyId)
                except Exception as e:
                    logger.error(f"Error whlie update additional product data {data.productId}")
                    continue


    async def create_product_data(self, **x) -> Optional[product_data.ProductData]:  
        start = time.time()
        default_id = f"{self.sku_prefix}-{x['acme.sku']}"
        try:
            product_model = self.product_dao.fetch_product(default_id)
            product_model.stock = self.parse_inventory_stock(x)
            product_model.price = self.make_price(x)
            product_model.cost = x['catalog_product_tier_price.price']
            return product_model
        except NoProductError:
            pass
        try:
            tag =  x['tags'] if x.get('tags') else ''
            product_model = product_data.ProductData(
                productId=default_id,
                cost=x['catalog_product_tier_price.price'],
                shortDescription=x.get("acme.short_description", ""),
                tagList=[y.strip() for y in tag.split(',') if y],
                productType='Kitchen & Dining Furniture Sets',
                trackInventory=True,
                brandName=self.brand_data.brandName,
                brandData=self.brand_data,
                taxable=True,
                additionalGroupId=x.get("acme.group", ''),
            )
            product_model.price = self.make_price(x)
            product_model.beforeSalePrice = x['acme.MSRP']
            if check_field_exists(x['acme.video']):
                video_url = f"https://www.youtube.com/embed/{x['acme.video']}"
                product_model.videoUrlList= [video_url]

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
            logger.error(f"Error while creating feature list {product_model.productId}")
            return None

        try:
            product_model.shipType = self.parse_shiptype_data(x)
        except Exception:
            logger.error(f"Error while make shiptype {product_model.productId}")
            return None    

        try:
            product_model.description = self.make_product_description(product_model)
        except Exception:
            logger.error(f"Error while make description {product_model.productId}")
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
            product_model.weightInfo = self.parse_weight_info(x)
        except Exception:
            logger.error(f"Error while make weight info data {product_model.productId} {traceback.format_exc()}")
            return None
        try:
            product_model.goodsMustInfo = self.parse_must_info_list(x, product_model.weightInfo)
        except Exception as e:
            logger.error(f"Error while make goodsmust info {product_model.productId} {str(e)}")
            return None
        try:
            product_model.additionalProductList = self.parse_additional_data_list(product_model)
        except Exception:
            logger.error(f"Error while make additional data {product_model.productId} {traceback.format_exc()}")
            pass

        try:
            product_model.productType = "Kitchen & Dining Furniture Sets"
            add_additional_tag_to_product(product_model)
        except Exception:
            logger.error(f"Error while make additional tags {product_model.productId} {traceback.format_exc()}")
        end = time.time()
        print(end - start, product_model.productId)
        return product_model

    def parse_inventory_stock(self, x: Dict) -> int:
        if check_field_exists(x['acme.la_qty']):
            return x['acme.la_qty']
        return 0

    def make_price(self, x: Dict) -> float:
        return round_up_decimals(x['catalog_product_tier_price.price'] * 1.20, decimals=0)

    def parse_additional_data_list(self, product_model: product_data.ProductData) -> float:
        if not product_model.additionalGroupId:
            return []
        df_list = self.fetch_matched_additional_list(
            product_model.additionalGroupId,
            product_model.productId
        )
        additional_list = []
        for _, data in df_list.iterrows():
            try:
                data = data.to_dict()
                thumbnail_image = self.parse_additional_thumbnail(data['acme.sku'], data)
                stock = self.parse_inventory_stock(data)
                additional_list.append(
                    product_data.AdditionalProductList(
                        productId=f"{self.sku_prefix}-{data['acme.sku']}",
                        thumbnailImage=thumbnail_image,
                        isSoldOut=stock==0,
                        productName=self.parse_title(data),
                    )
                )
            except Exception as e:
                logger.error(f"Error while make singe additional data {product_model.productId} {str(e)}")
        return additional_list
    
    def parse_title(self, x: Dict) -> str:
        name = x['acme.name']
        collection_name = x['acme.collection_name']
        finish_name = x['acme.catalog_finish']
        if finish_name is None:
            finish_name = ""
        else:
            finish_name = f'with {finish_name.replace("&", "and")}' 

        if collection_name.lower() in name.lower():
            return f"Acme Furniture {name} {finish_name}".strip()
        else:
            return f"Acme Furniture {collection_name} Collection {name} {finish_name}".strip()
    
    async def parse_main_image_list(self, sku ,x: Dict) -> List[str]:
        image_array = x['Image Array'].replace('[', '').replace(']', '').split(',')
        return await upload_urls_to_s3_list(image_array, f'/{sku}', quality=90, fix_image_width=775 )

    def parse_additional_thumbnail(self, sku ,x: Dict) -> str:
        default_id = f"{self.sku_prefix}-{sku}"
        image_array = x['Image Array'].replace('[', '').replace(']', '').split(',')
        img = image_array[0]
        img = upload_url_to_s3(img, f'/{default_id}', quality=70, resize_tuple=(80, 80))
        return img

    def parse_warranty(self, x: Dict) -> str:
        warranty_header = f'<p class="warranty-header">Warranty Period: {x["Warranty Length"]}</p>'
        warranty_body = f"<p>{x['Warranty Term']}</p>"
        return f"{warranty_header}{warranty_body}{self.brand_data.warranty}"

    def parse_delivery_data(self) -> product_data.DeliveryData:
        return product_data.DeliveryData(
            price=0,
            cost=0,
            deliveryType=FREIGHT,
            minDays=2,
            maxDays=10
        )
    
    def convert_weight_data(self, x: Dict, key: str) -> float:
        length = x[key]
        if length is None:
            return 0.0
        if type(length) is str and not length.isdigit():
            if '~' in length:
                length = float(length.split("~")[-1])
            elif '-' in length:
                length = float(length.split("-")[-1])
        return float(length)


    def parse_weight_info(self, x: Dict) -> product_data.WeightInfo:
        weight_info =  product_data.WeightInfo()
        weight_info.packageWeight = self.convert_weight_data(x, 'acme.package_weight')
        weight_info.packageHeight = self.convert_weight_data(x, 'acme.package_height')
        weight_info.packageLength = self.convert_weight_data(x, 'acme.package_length')
        weight_info.packageWidth = self.convert_weight_data(x, 'acme.package_width')
        weight_info.weight = self.convert_weight_data(x, 'acme.product_weight')
        weight_info.height = self.convert_weight_data(x, 'acme.product_height')
        weight_info.length = self.convert_weight_data(x, 'acme.product_length')
        weight_info.width = self.convert_weight_data(x, 'acme.product_width')
        if weight_info.packageWeight == 0:
            weight_info.packageWeight = weight_info.weight
        if not weight_info.packageHeight:
            weight_info.packageHeight = weight_info.height
            weight_info.packageLength = weight_info.length
            weight_info.packageWidth = weight_info.width
        return weight_info
        

    def parse_must_info_list(self, x:Dict, weight_info: product_data.WeightInfo) -> List[product_data.MustInfo]:
        must_info_list = []
        if check_field_exists(x["acme.product_type"]):
            must_info_list.append(product_data.MustInfo(
                key="Product Type",
                valueList=[
                    str(x["acme.product_type"])
                ],

            ))
        if check_field_exists(x["acme.catalog_finish"]):
            must_info_list.append(product_data.MustInfo(
                key="Finish",
                valueList=[
                    str(x["acme.catalog_finish"])
                ],

            ))
        if check_field_exists(x["acme.material_detail"]):
            must_info_list.append(product_data.MustInfo(
                key="Material Detail",
                valueList=[
                    str(x["acme.material_detail"])
                ],

            ))

        if check_field_exists(x["acme.package_type"]):
            must_info_list.append(product_data.MustInfo(
                key="Package Type",
                valueList=[
                    str(x["acme.package_type"])
                ],

            ))
        if weight_info.weight:
            must_info_list.append(product_data.MustInfo(
                key="Weight",
                valueList=[
                    f"{weight_info.weight} lbs"
                ],

            ))
        if weight_info.packageWeight:
            must_info_list.append(product_data.MustInfo(
                key="Package Weight",
                valueList=[
                    f"{weight_info.packageWeight} lbs"
                ],
            ))
        if weight_info.height:
            must_info_list.append(product_data.MustInfo(
                key="Dimension",
                valueList=[
                    f"{weight_info.height}H x {weight_info.width}W x {weight_info.length}L"
                ],

            ))
      
        return must_info_list
    
    def parse_feature_list(self, x: Dict) -> List[str]:
        if check_field_exists(x['acme.description']):
            feature_list = x['acme.description'].split(':')
            feature_list = [col.replace("(", '').replace(")", '').strip() for col in feature_list if col.strip()]
            return feature_list
        return []
