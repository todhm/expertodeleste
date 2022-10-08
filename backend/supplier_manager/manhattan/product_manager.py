from tabnanny import check
from typing import List, Dict, Optional
import logging
import traceback
import re

import pandas as pd
from furl import furl

from models import product_data
from config import ProductionConfig
from dataparser.excel_data import check_field_exists
from data_types.shipping import FREIGHT
from data_types.ship_type import LTL, PARCEL, ShipTypeType
from supplier_manager.default_product_manager import DefaultProductManager
from shopify_dao.product import ProductDao
from errors.products import NoProductError
from dataparser.image import upload_urls_to_s3_list
from dataparser.numbers import round_up_decimals
from dataparser.tags import add_additional_tag_to_product


logger = logging.getLogger(__name__)


class ManhattanProductManager(DefaultProductManager):

    image_col_list = [
        'PhotoBucket: White Image -A',	
        'PhotoBucket: Live Image -B',
        'PhotoBucket: Internal Image - C',
        'PhotoBucket: Nuanced Image -D',
        'PhotoBucket: - E',
        'PhotoBucket: - F',	
        'PhotoBucket: -G',
        'PhotoBucket: -H',
        'PhotoBucket: -I',	
        'PhotoBucket: - J'
    ]
    video_col_list = [
        'Manual Video Link - YouTube',
        'Product Features Video Link YouTube',
    ]

    def __init__(
        self, 
        product_dao: ProductDao,
        brand_data: product_data.BrandData, 
        product_path: str,
        stock_path: str,
        sku_prefix: str = 'MH',
        start_index: int = 0
    ):
        self.sku_prefix = sku_prefix
        self.brand_data = brand_data
        self.product_dao = product_dao
        product_df = pd.read_excel(product_path)
        inventory_df = pd.read_excel(stock_path)
        product_df = product_df.set_index('Sku').join(inventory_df.set_index('Item')).reset_index()
        self.product_df: pd.DataFrame = product_df[
            (product_df['Category'].str.match(self.dining_match_re, case=False, na=False))
        ].reset_index()
        self.product_df = self.product_df.rename(
            columns=lambda x: x.strip().replace("\n", ' ').replace("\t", ' ').replace("  ", ' ').replace("Box1", "Box 1")
        ).rename(columns=lambda x: ' '.join([i for i in x.split(' ') if i.strip()]).replace("Shjp Type", "Ship Type"))
        self.product_df = self.product_df.dropna(subset=["Model"]).reset_index(drop=True)
        self.product_df = self.product_df[start_index:].reset_index(drop=True)

    async def fetch_all_product_data_list(self) -> List[product_data.ProductData]:
        product_list = []
        for _, df_group in self.product_df.groupby("Model"):
            row_list = []
            for _, row in df_group.iterrows():
                row_list.append(row.to_dict())
            product_list.append(await self.create_product_data(row_list))
        return product_list

    async def upsert_all_product_data(self):
        for productid, df_group in self.product_df.groupby("Model"):
            row_list = []
            for _, row in df_group.iterrows():
                row_list.append(row.to_dict())
            try:
                data = await self.create_product_data(row_list)
                if not data:
                    continue
                print(data.productId, "SUCCESS")
            except Exception as e:
                logger.error(f"Error while maake daata {str(e)} {productid} {traceback.format_exc()}")
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

    def parse_inventory_stock(self, x: Dict) -> int:
        return int(x['Quantity'])

    def make_price(self, x: Dict) -> float:
        return round_up_decimals(x['Wholesale'] * 1.25, decimals=0)
    
    def fetch_single_row(self, sku_id: str) -> Dict:
        row = self.product_df[self.product_df['Model'].apply(lambda x: f"{self.sku_prefix}-{x}") == sku_id]
        return row.to_dict('records')[0]

    def make_base_sku_data(self, row_list: List[Dict], product_model: product_data.ProductData) -> None:
        sku_list = []
        if len(row_list) > 1:
            for row in row_list:
                sku = product_data.Sku(
                    skuId=str(row['Sku']),
                    cost=row['Wholesale'],
                    upcCode=row['UPC CODE'],
                    price=self.make_price(row),
                    beforeSalePrice=row['MSRP'],
                    weight=row['Total Product Shipping Weight'],
                )
                sku.optionList = [product_data.OptionData(
                    optionName="Color",
                    optionValue=row["Color"]
                )]
                sku.warehouseInfo = [product_data.WarehouseData(
                    stock=row['Quantity']
                )]
                sku_list.append(sku)
            product_model.skuList = sku_list
            product_model.optionNameList = ["Color"]
        return sku_list
    
    def update_sku_list(self, product_model: product_data.ProductData ,row_list: List[Dict]) -> None:
        if product_model.skuList:
            for sku in product_model.skuList:
                matched_row = list(filter(lambda x: str(x['Sku']) == str(sku.skuId), row_list))[0]
                sku.cost = matched_row['Wholesale']
                sku.price = self.make_price(matched_row)
                sku.warehouseInfo = [product_data.WarehouseData(
                    stock=matched_row['Quantity']
                )]

    def parse_shiptype_data(self, x: Dict) -> ShipTypeType:
        if 'ltl' in x['Ship Type'].lower():
            return LTL
        else:
            return PARCEL

    def parse_video_url_list(self, x: Dict) -> List[str]:
        for col in self.video_col_list:
            if check_field_exists(x[col]):
                if check_field_exists(x[col]):
                    if 'watch?' in x[col]:
                        furl_object = furl(x[col])
                        embedid = furl_object.args['v']
                        embed_link = f"https://www.youtube.com/embed/{embedid}"
                        return [embed_link]
                    elif 'youtu.be/' in x[col]:
                        embedid = x[col].split('/')[-1]
                        embed_link = f"https://www.youtube.com/embed/{embedid}"
                        return [embed_link]
        return []

    async def create_product_data(self, row_list: List[Dict]) -> Optional[product_data.ProductData]:  
        default_id = f"{self.sku_prefix}-{row_list[0]['Model']}"
        try:
            product_model = self.product_dao.fetch_product(default_id)
            product_model.upcCode = row_list[0].get('UPC CODE', '')
            self.update_sku_list(product_model, row_list)
            return product_model
        except NoProductError:
            pass
        try:
            product_model = product_data.ProductData(
                productId=default_id,
                cost=row_list[0]['Wholesale'],
                beforeSalePrice=row_list[0]['MSRP'],
                price=self.make_price(row_list[0]),
                shortDescription=row_list[0]['Romantic Description'],
                tagList=[y.strip() for y in row_list[0].get("tags", '').split(',') if y],
                productType='Kitchen & Dining Furniture Sets',
                trackInventory=True,
                brandName=self.brand_data.brandName,
                brandData=self.brand_data,
                upcCode=row_list[0]['UPC CODE'],
                taxable=True,
            )
            self.make_base_sku_data(row_list, product_model)
            product_model.stock = self.parse_inventory_stock(row_list[0])
        except Exception:
            logger.error(f"Error while make base product data {traceback.format_exc()}")
            return None

        try:
            product_model.shipType = self.parse_shiptype_data(row_list[0])
        except Exception:
            logger.error(f"Error while make shiptype {product_model.productId}")
            return None

        try:
            product_model.videoUrlList = self.parse_video_url_list(row_list[0])
        except Exception:
            logger.error(f"Error while crawl video url {traceback.format_exc()}")
            return None
        try:
            product_model.goodsName = self.parse_title(row_list[0])
        except Exception:
            logger.error(f"Error while make goods Name {product_model.productId}")
            return None

        try:
            await self.parse_main_image_list(product_model, row_list)
        except Exception:
            logger.error(f"Error while make main image list {product_model.productId} {traceback.format_exc()}")
            return None

        try:
            product_model.featureList = self.parse_feature_list(row_list[0])
        except Exception:
            logger.error(f"Error while make feature list {product_model.productId} {traceback.format_exc()}")
            return None

        try:
            prop_65 = check_field_exists(row_list[0]['Prop 65 Required']) and row_list[0]['Prop 65 Required '] == "Yes"
            product_model.description = self.make_product_description(product_model, prop_sixty_five=prop_65)
        except Exception:
            logger.error(f"Error while make description {product_model.productId} {traceback.format_exc()}")
            return None
        
        try:
            product_model.warranty = self.brand_data.warranty
        except Exception:
            logger.error(f"Error while make warranty {product_model.productId}")
            return None

        try:
            product_model.deliveryDataList = [self.parse_delivery_data()]
        except Exception:
            logger.error(f"Error while delivery data {product_model.productId}")
            return None
        try:
            self.parse_weight_info(product_model, row_list)
        except Exception:
            logger.error(f"Error while make weight info data {product_model.productId} {traceback.format_exc()}")
            return None
        try:
            product_model.goodsMustInfo = self.parse_must_info_list(row_list[0])
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
            self.parse_tag_list(product_model, row_list[0])
            add_additional_tag_to_product(product_model)
        except Exception:
            logger.error(f"Error while make additional tags {product_model.productId} {traceback.format_exc()}")
            return None
        return product_model

    def make_price_row_list(self, x: Dict) -> float:
        return round_up_decimals(x['US $'] * 1.25, decimals=0)
    
    def parse_title(self, x: Dict) -> str:
        name = x['Collection Variation - Collection Model Parent Name']
        return f"Manhattan Comfort {name}"

    def parse_video(self, x: Dict) -> str:
        name = x['Video']
        server_url = f"https://{ProductionConfig.BUCKET_NAME}.s3.{ProductionConfig.S3_REGION}.amazonaws.com/videos/{name}"
        return server_url

    async def parse_main_image_list(self, product_model: product_data.ProductData ,row_list: List[Dict]) -> List[str]:
        image_array = []
        for row in row_list:
            for col in self.image_col_list:
                if check_field_exists(row[col]):
                    image_array.append(row[col])
        return_s3_list =  await upload_urls_to_s3_list(
            image_array, f'/{self.sku_prefix}/{product_model.productId}/', quality=90, fix_image_width=775
        )
        product_model.mainImageList = return_s3_list
        image_map = {}
        for origin, new_url in zip(image_array, return_s3_list):
            image_map[origin] = new_url
        if product_model.skuList:
            for sku, row in zip(product_model.skuList, row_list):
                if check_field_exists(row['PhotoBucket: White Image -A']):
                    sku.optionList[0].optionImage = image_map[row['PhotoBucket: White Image -A']]
        
    def parse_delivery_data(self) -> product_data.DeliveryData:
        return product_data.DeliveryData(
            price=0,
            cost=0,
            deliveryType=FREIGHT,
            minDays=3,
            maxDays=10,
            freightDiscountRate=0.8
        )

    def parse_tag_list(self, product_model: product_data.ProductData, x: Dict) -> None:
        if check_field_exists(x['Ship Type']):
            product_model.add_tag(x['Ship Type'])
        if check_field_exists(x['Specific Color']):
            color = x['Specific Color']
            if re.search(self.dark_color_re, color, flags=re.IGNORECASE):
                product_model.add_tag("Dark")
            elif re.search(self.bright_color_re, color, flags=re.IGNORECASE):
                product_model.add_tag("Bright")
        if check_field_exists(x['Category']):
            category = x['Category']
            if re.search(r"coffee.*table", category, flags=re.IGNORECASE):
                product_model.add_tag("Simple")
                return
            if "outdoor" in category.lower():
                product_model.add_tag("Outdoor")
                return
        if check_field_exists(x["Style"]):
            style = x["Style"]
            if "scandinavian" in style.lower():
                product_model.add_tag("Simple")
            elif "modern" in style.lower():
                product_model.add_tag("Modern")
            elif "traditional" in style.lower():
                product_model.add_tag("Classics")
            

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

    def parse_weight_info(self, product_model: product_data.ProductData, row_list: List = []) -> None:
        weight_info_list = self.parse_single_row_weight_info(row_list[0])
        product_model.weightInfo = weight_info_list[0]
        product_model.weightInfoList = weight_info_list
        if product_model.skuList:
            for row, sku in zip(row_list, product_model.skuList):
                weight_info_list = self.parse_single_row_weight_info(row)
                sku.weightInfoList = weight_info_list
                sku.weightInfo = weight_info_list[0]

    def parse_single_row_weight_info(self, x: Dict) -> List[product_data.WeightInfo]:
        weight_info_list = []
        for i in range(1, 10):
            if check_field_exists(x[f'Shipping Weight (Box {i})']):
                weight_info_list.append(product_data.WeightInfo(
                    width=x['Product Depth'],
                    height=x['Product Height'],
                    length=x['Product Length ->'],
                    weight=x['Product Weight'],
                    packageWeight=x[f'Shipping Weight (Box {i})'],
                    packageHeight=x[f'Carton Height (Top to Bottom) (Box {i})'],
                    packageWidth=x[f'Carton Depth (Front to Back) (Box {i})'],
                    packageLength=x[f'Carton Length (Side to Side) (Box {i})'],
                ))
        return weight_info_list
        

    def parse_must_info_list(self, x:Dict) -> List[product_data.MustInfo]:
        must_info_list = []
        must_info_data_map = [
            {"key": "Made IN", "name": "Country Of Origin"},
            {"key": "Room Setting", "name": "Room Setting"},
            {"key": "Frame Material", "name": "Frame Material"},
            {"key": "Feet Material -", "name": "Feet Material"},
            {"key": "Fabric Material", "name": "Fabric Material"},
            {"key": "Back Finish", "name": "Back Finish"},
            {"key": "Table/ Item Shape", "name": "Shape"},
            {"key": "Chair Back Dimensions", "name": "Chair Back Dimensions"},
            {"key": "W X H X D", "name": "Product Size(inches)"},
            {"key": "Recommended TV size", "name": "Recommended TV size"},
            {"key": "Assembly Required", "name": "Assembly Required"},
        ]
        for mustrow in must_info_data_map:
            if check_field_exists(x[mustrow["key"]]):
                must_info_list.append(product_data.MustInfo(
                    key=mustrow["name"],
                    valueList=[
                        str(x[mustrow["key"]])
                    ],
                ))
        return must_info_list

    def parse_feature_list(self, x: Dict) -> List[str]:
        li_list = []
        li_list = []
        if check_field_exists(x['Bullet Feature 1 ( Short Description - 1 Sentence Usage )']):
            li_list.append(x['Bullet Feature 1 ( Short Description - 1 Sentence Usage )'])
        for i in range(2, 9):
            feature_col = f"Bullet Feature {i}"
            if check_field_exists(x[feature_col]):
                li_list.append(x[feature_col])
        return li_list
