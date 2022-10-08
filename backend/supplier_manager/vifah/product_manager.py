from typing import List, Dict, Optional
import logging
import traceback
import re

import pandas as pd
from furl import furl
import requests

from config import ProductionConfig
from data_types.ship_type import LTL, PARCEL, ShipTypeType
from models import product_data
from dataparser.excel_data import check_field_exists
from data_types.shipping import FIXED
from supplier_manager.default_product_manager import DefaultProductManager
from shopify_dao.product import ProductDao
from errors.products import NoProductError
from dataparser.tags import add_additional_tag_to_product
from dataparser.image import upload_urls_to_s3_list
from dataparser.strings import parse_specification_string


logger = logging.getLogger(__name__)


class VifahProductManager(DefaultProductManager):


    def __init__(
        self, 
        product_dao: ProductDao, 
        brand_data: product_data.BrandData, 
        home_path: str, 
        outdoor_path:str, 
        office_path:str,
        inventory_product_path: str,
        sku_prefix: str = 'VI',
        start_index: int = 0
    ):
        self.sku_prefix = sku_prefix
        self.brand_data = brand_data
        self.product_dao = product_dao
        product_df = pd.read_excel(home_path, header=None)
        outdoor_df = pd.read_excel(outdoor_path, header= None)
        office_df = pd.read_excel(office_path, header= None, skiprows=1)
        inventory_df = pd.read_csv(inventory_product_path)
        outdoor_df = self.squeeze_header(outdoor_df).reset_index(drop=True)
        product_df = self.squeeze_header(product_df).reset_index(drop=True)
        office_df = self.squeeze_header(office_df).reset_index(drop=True)
        product_df = product_df.loc[:,~product_df.columns.duplicated()]
        rename_dict = {
            'MAP\n(If Applicable\nNOT included shipping)': 'MAP',
            "Official Dropship Cost 2022": "cost",
            'Shipping cost\n(If applicable)': "shippingCost",
            "Shipping cost\n(If Applicable)": "shippingCost",
            'MAP\n(If Applicable - NOT included shipping)': "MAP",
            'Product Dims.L': "Product Specification.L",
            'Product Dims.W': "Product Specification.W",
            'Product Dims.H': "Product Specification.H",
            'Product Dims.LBS': "Product Specification.LBS",
            'Package Dims.L': "Packaging Specification.L",
            'Package Dims.W': "Packaging Specification.W",
            'Package Dims.H': "Packaging Specification.H",
            'Package Dims.LBS': "Packaging Specification.LBS",
            "Image7": "Image 7",
            'LTL/Ground': "Shipping",
        }
        for i in range(1, 8):
            rename_dict[f"Image Link {i}"] = f"Image {i}"
        product_df = product_df.rename(columns=rename_dict)
        outdoor_df = outdoor_df.rename(columns=rename_dict)
        office_df = office_df.rename(columns=rename_dict)
        product_df = pd.concat([product_df, outdoor_df, office_df])
        product_df = product_df.set_index('SKU').join(inventory_df.set_index('SKU')).reset_index()
        self.product_df: pd.DataFrame = product_df[
            (product_df['Product Name'].str.match(self.dining_match_re, case=False, na=False))
            &
            product_df['Product Name'].str.match(r"^(?!.*outdoor.*tile).*$", case=False, na=False)
            &
            product_df['Product Name'].str.match(r"^(?!.*adjustable.*desk).*$", case=False, na=False)
            &
            product_df['Product Name'].str.match(r"^(?!.*bar.*stool).*$", case=False, na=False)
        ]
        self.product_df = self.product_df[start_index:].reset_index(drop=True)

    def download_videos(self):
        data_map = {}
        for x in self.product_df['AI Video 1']:
            if check_field_exists(x):
                fname = self.download_dropbox_video_url(x, data_map = data_map)
                data_map[fname] = True
                print(fname)

    def download_dropbox_video_url(self, url: str, folder=f"./datacollections/vifah/videos", data_map: Dict = {}) -> str:
        furl_object = furl(url)
        furl_object.args['dl'] = "1"
        url = furl_object.url
        fname = url.split("/")[-1].replace("?dl=1", "")
        if data_map.get(fname):
            return fname
        r = requests.get(url, stream=True)
        file_name = f"{folder}/{fname}"
        with open(file_name, 'wb') as f:
            for chunk in r.iter_content(chunk_size = 1024*1024):
                if chunk:
                    f.write(chunk)
        return fname

    def drop_duplicate_join(self, datalist: List[str]) -> str:
        before_data = None
        newdatalist = []
        lbs_list = ['Product Specification', 'Packaging Specification', "Product Dims", "Package Dims"]
        color_list = ['Product Images']
        for data in datalist:
            if data and data != before_data:
                if data == "LBS" and before_data not in lbs_list:
                    continue
                if data == "Color" and before_data in color_list:
                    continue
                newdatalist.append(data)
                before_data = data
        if len(newdatalist) == 2 and newdatalist[0] == 'Product Information':
            newdatalist = newdatalist[1:]
        return '.'.join(newdatalist)
            
    def squeeze_header(self, df: pd.DataFrame) -> pd.DataFrame:
        df.iloc[0:2] = df.iloc[0:2].fillna(method='ffill', axis=1)
        df.iloc[0:2] = df.iloc[0:2].fillna('')
        df.columns = df.iloc[0:2].apply(lambda x: self.drop_duplicate_join(x), axis=0)
        df = df.iloc[2:]
        return df

    async def fetch_all_product_data_list(self) -> List[product_data.ProductData]:
        product_list = []
        for _, data in self.product_df.iterrows():
            product_list.append(await self.create_product_data(data.to_dict()))
        return product_list

    async def upsert_all_product_data(self):
        for idx, row in self.product_df.iterrows():
            productrow = None
            productrow = row.to_dict()
            try:
                data = await self.create_product_data(productrow)
                if not data:
                    continue
                print(data.productId, "SUCCESS", idx)
            except Exception as e:
                logger.error(f"Error while making daata {str(e)} {idx}")
            try:
                if data.shopifyId:
                    self.product_dao.upsert_product(data, selected_keys=[
                        "variants",
                    ], update_meta=False)
                else:
                    self.product_dao.upsert_product(data)
            except Exception as e:
                logger.error(f"Error while upsert data {str(e)} {data.productId} {idx}")

    def parse_warranty(self) -> str:
        return self.brand_data.warranty

    def parse_video_url(self, x: Dict) -> str:
        furl_object = furl(x["AI Video 1"])
        furl_object.args['dl'] = "1"
        url = furl_object.url
        fname = url.split("/")[-1].replace("?dl=1", "")
        server_url = f"https://{ProductionConfig.BUCKET_NAME}.s3.{ProductionConfig.S3_REGION}.amazonaws.com/videos/vifah/{fname}"
        return server_url

    def fetch_single_row(self, sku_id: str) -> Dict:
        row = self.product_df[self.product_df['SKU'].apply(lambda x: f"{self.sku_prefix}-{x}") == sku_id]
        return row.to_dict('records')[0]

    async def create_product_data(self, x: Dict) -> Optional[product_data.ProductData]:  
        default_id = f"{self.sku_prefix}-{x['SKU']}"
        try:
            product_model = self.product_dao.fetch_product(default_id)
            product_model.stock = self.parse_inventory_stock(x)
            product_model.price = self.make_price(x)
            product_model.cost = x['cost']
            product_model.upcCode = x['EAN/UPC']
            return product_model
        except NoProductError:
            pass
        try:
            tag =  x['tags'] if x.get('tags') else ''
            product_model = product_data.ProductData(
                productId=default_id,
                cost=x['cost'],
                shortDescription=x.get("Description", ""),
                tagList=[y.strip() for y in tag.split(',') if y],
                productType='Kitchen & Dining Furniture Sets',
                trackInventory=True,
                brandName=self.brand_data.brandName,
                brandData=self.brand_data,
                taxable=True,
                upcCode=x['EAN/UPC']
            )
            product_model.price = self.make_price(x)
            self.make_before_price(product_model)
            if check_field_exists(x['AI Video 1']):
                product_model.videoUrlList = [self.parse_video_url(x)]
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
            logger.error(f"Error while make ")

        try:
            product_model.shipType = self.parse_shiptype_data(x)
        except Exception:
            logger.error(f"Error while make description {product_model.productId} {traceback.format_exc()}")
            return None

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
            product_model.deliveryDataList = [self.parse_delivery_data(x)]
        except Exception:
            logger.error(f"Error while delivery data {product_model.productId}")
            return None

        try:
            product_model.weightInfoList = self.parse_weight_info(x)
            product_model.weightInfo = product_model.weightInfoList[0]
        except Exception:
            logger.error(f"Error while make weight info data {product_model.productId} {traceback.format_exc()}")
            return None
        try:
            product_model.goodsMustInfo = self.parse_must_info_list(x)
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
        if check_field_exists(x['QUANTITY']):
            return int(x['QUANTITY'])
        return 0

    def make_price(self, x: Dict) -> float:
        return x['MAP']
    
    def parse_title(self, x: Dict) -> str:
        name = x['Product Name']
        return name

    def parse_video(self, x: Dict) -> str:
        name = x['Video']
        server_url = f"https://{ProductionConfig.BUCKET_NAME}.s3.{ProductionConfig.S3_REGION}.amazonaws.com/videos/{name}"
        return server_url
    
    # VPN없으면 작동안함
    async def parse_main_image_list(self, sku ,x: Dict) -> List[str]:
        image_array = []
        for i in range(1, 8):
            if check_field_exists(x[f'Image {i}']):
                image_url = x[f'Image {i}']
                fobject = furl(image_url)
                fobject.args['dl'] = "1"
                url = fobject.url
                image_array.append(url)
        return await upload_urls_to_s3_list(image_array, f'/{sku}', quality=90, fix_image_width=775)

    def parse_delivery_data(self, x: Dict) -> product_data.DeliveryData:
        delivery_data =  product_data.DeliveryData(
            price=x['shippingCost'],
            cost=x['shippingCost'],
            deliveryType=FIXED,
            minDays=2,
            maxDays=5,
        )
        if check_field_exists(x["Shipping"]):
            delivery_data.deliveryName = x['Shipping']
        return delivery_data

    def parse_tag_list(self, product_model: product_data.ProductData, x: Dict) -> None:
        if check_field_exists(x['Finish']):
            color = x['Finish']
            if re.search(self.dark_color_re, color, flags=re.IGNORECASE):
                product_model.add_tag("Dark")
            elif re.search(self.bright_color_re, color, flags=re.IGNORECASE):
                product_model.add_tag("Bright")
        if check_field_exists(x['Color']):
            color = x['Color']
            if re.search(self.dark_color_re, color, flags=re.IGNORECASE):
                product_model.add_tag("Dark")
            elif re.search(self.bright_color_re, color, flags=re.IGNORECASE):
                product_model.add_tag("Bright")

        if check_field_exists(x['Product Name']):
            name = x['Product Name']
            if re.search(self.simple_re, name, flags=re.IGNORECASE):
                product_model.add_tag("Simple")
            elif re.search(self.outdoor_re, name, flags=re.IGNORECASE):
                product_model.add_tag("Outdoor")

    def parse_shiptype_data(self, x: Dict) -> ShipTypeType:
        ship_type = x['Shipping']
        if ship_type == "LTL":
            return LTL
        else:
            return PARCEL

    @classmethod
    def parse_weight_info(cls, x: Dict) -> List[product_data.WeightInfo]:
        product_dim_not_number = check_field_exists(x['Product Specification.L']) and not check_field_exists(x['Product Specification.W'])
        package_dim_not_number = check_field_exists(x['Packaging Specification.L']) and not check_field_exists(x['Packaging Specification.W'])
        package_dim_number = check_field_exists(x['Packaging Specification.L']) and check_field_exists(x['Packaging Specification.W'])
        if package_dim_not_number:
            weight_info_list = []
            package_row_list = [x for x in x['Packaging Specification.L'].split('\n') if 'lbs' in x.lower()]
            product_row_list = [x for x in x['Product Specification.L'].split('\n') if 'lbs' in x.lower()]
            for idx, package in enumerate(package_row_list):
                if ":" in package:
                    data_tuple = parse_specification_string(package)
                    x['Packaging Specification.W'] = data_tuple[0]
                    x['Packaging Specification.H'] = data_tuple[1]
                    x['Packaging Specification.L'] = data_tuple[2] 
                    x['Packaging Specification.LBS'] = data_tuple[3]
                if product_dim_not_number:
                    data_tuple = parse_specification_string(product_row_list[idx])
                    x['Product Specification.W'] = data_tuple[0]
                    x['Product Specification.H'] = data_tuple[1]
                    x['Product Specification.L'] = data_tuple[2] 
                    x['Product Specification.LBS'] = data_tuple[3]
                weight_info_list.append(
                    product_data.WeightInfo(
                        width=x['Product Specification.W'],
                        height=x['Product Specification.H'],
                        length=x['Product Specification.L'],
                        weight=x['Product Specification.LBS'],
                        packageWeight=x['Packaging Specification.LBS'],
                        packageHeight=x['Packaging Specification.H'],
                        packageWidth=x['Packaging Specification.W'],
                        packageLength=x['Packaging Specification.L'],
                    )
                )
            return weight_info_list
        if package_dim_number:
            if product_dim_not_number:
                for table in x['Product Specification.L'].split('\n'):
                    if 'table' in table.lower():
                        data_tuple = parse_specification_string(table)
                        x['Product Specification.W'] = data_tuple[0]
                        x['Product Specification.H'] = data_tuple[1]
                        x['Product Specification.L'] = data_tuple[2] 
                        x['Product Specification.LBS'] = data_tuple[3]
            weight_info =  product_data.WeightInfo(
                width=x['Product Specification.W'],
                height=x['Product Specification.H'],
                length=x['Product Specification.L'],
                weight=x['Product Specification.LBS'],
                packageWeight=x['Packaging Specification.LBS'],
                packageHeight=x['Packaging Specification.H'],
                packageWidth=x['Packaging Specification.W'],
                packageLength=x['Packaging Specification.L'],
            )
            return [weight_info]

    def parse_must_info_list(self, x:Dict) -> List[product_data.MustInfo]:
        must_info_list = []
        if check_field_exists(x["Country of origin"]):
            must_info_list.append(product_data.MustInfo(
                key="Country Of Origin",
                valueList=[
                    str(x["Country of origin"])
                ],
            ))
        if check_field_exists(x["Finish"]):
            must_info_list.append(product_data.MustInfo(
                key="Finish",
                valueList=[
                    str(x["Finish"])
                ],
            ))
        if check_field_exists(x["Specifications"]):
            for feature in x['Specifications'].split('\n'):
                if feature and ":" in feature:
                    must_info_list.append(product_data.MustInfo(
                        key=feature.split(":")[0].strip(),
                        valueList=[
                            feature.split(":")[1].strip()
                        ],

                    ))
        if check_field_exists(x['Features and Specification']):
            for feature_col in x['Features and Specification'].split('\n'):
                if feature_col.strip() and ":" in feature_col:
                    must_info_list.append(product_data.MustInfo(
                        key=feature_col.split(":")[0].strip(),
                        valueList=[
                            feature_col.split(":")[1].strip()
                        ],
                    ))
        if check_field_exists(x['Features']):
            for feature_col in x['Features'].split('\n'):
                if feature_col.strip() and ":" in feature_col:
                    must_info_list.append(product_data.MustInfo(
                        key=feature_col.split(":")[0].strip(),
                        valueList=[
                            feature_col.split(":")[1].strip()
                        ],
                    ))
        return must_info_list
    
    def parse_feature_list(self, x: Dict) -> List[str]:
        li_list = []
        if check_field_exists(x['Features and Specification']):
            for feature_col in x['Features and Specification'].split('\n'):
                if feature_col.strip() and ":" not in feature_col:
                    li_list.append(feature_col)

        if check_field_exists(x['Features']):
            for feature_col in x['Features'].split('\n'):
                if feature_col.strip() and ":" not in feature_col:
                    li_list.append(feature_col)
        return li_list