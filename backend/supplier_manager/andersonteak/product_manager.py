from typing import List, Dict
import logging
import traceback
import re
import random

import pandas as pd

from models import product_data
from dataparser.excel_data import check_field_exists
from data_types.shipping import FIXED
from data_types.ship_type import ShipTypeType, PARCEL, LTL
from supplier_manager.default_product_manager import DefaultProductManager
from shopify_dao.product import ProductDao
from errors.products import NoProductError
from dataparser.image import upload_url_to_s3
from dataparser.dropbox import parse_img_url_from_dropbox
from dataparser.tags import add_additional_tag_to_product


logger = logging.getLogger(__name__)


class AndersonTeakProductManager(DefaultProductManager):


    def __init__(self, product_dao: ProductDao, brand_data: product_data.BrandData, default_product_path: str, inventory_product_path: str, sku_prefix: str = "AT"):
        self.sku_prefix = sku_prefix
        self.brand_data = brand_data
        self.product_dao = product_dao
        xls = pd.ExcelFile(default_product_path)
        self.inventory_df: pd.DataFrame = pd.read_csv(inventory_product_path)
        filter_adset_list = [
            'Bar Folding Table',
            'Adam Classic Serving Table',
            'Dining Table Set',
            'Bar Set',
            'Bistro Table Set',
            'Deep Seating Set',
            'Bench Set',
            'Dining Set',
            'Deep Seating / Modular Set',
            'Folding Bar Set',
            'Bistro Set',
            'Coffee Table Set',
            'Rocker Set',
            'Sun Lounger Set',
            'Bar Table Set',
            'Rocking Chair Set',
            'Recliner Set',
            'Modular Set',
            'Side Table Set',
            'Bellagio Deep Seating Set',
            'Bellagio Dining Set',
            'Milano Dining Set',
            'Sorrento Dining Set',
            'Bella Side Table w/ Marble Top',
            'Bar Table',
        ]
        self.product_df: pd.DataFrame = pd.read_excel(xls, 'Bulkload', header=1).dropna(subset=['Product Name']).reset_index(drop=True)
        self.product_df = self.product_df[self.product_df['Collection Ad Copy'].isin(filter_adset_list)].reset_index(drop=True)
        self.cushion_info_df: pd.DataFrame = pd.read_excel(xls, 'Furniture comes with cushion', header=2).reset_index(drop=True)
        self.with_cushion_list: List[str] = list(self.cushion_info_df['SKU'])
        self.cushion_price_df: pd.DataFrame = pd.read_excel(xls, 'Cushion for', header=2).dropna(subset=['MAP'])
        self.cushion_price_df.rename(
            columns={'Unnamed: 0': 'SKU'}, 
            inplace=True
        )
        self.cushion_price_df['cushionFor'] = self.cushion_price_df['SKU'].apply(lambda x: '-'.join(x.split('-')[1:-1]))
        self.no_cushion_message: str = 'Cushion is not included'
        self.feature_column_list: List[str] = [f'Feature {i}' for i in range(1, 15)]
        self.without_cushion_df: pd.DataFrame = self.product_df[self.product_df[self.feature_column_list + ['Manufacturer Model Number']].apply(lambda x: self.filter_cushon_df(**x), axis=1)]
        self.with_cushioin_df: pd.DataFrame = self.product_df[self.product_df[self.feature_column_list + ['Manufacturer Model Number']].apply(lambda x: self.filter_cushon_df(**x) is False, axis=1)]


    def fetch_all_product_data_list(self) -> List[product_data.ProductData]:
        return list(self.product_df.apply(lambda x: self.create_product_data(x), axis=1))
    
    def fetch_cushion_list(self) -> pd.DataFrame:
        return self.cushion_price_df[
            self.cushion_price_df['cushionFor'].isin(list(self.without_cushion_df['Manufacturer Model Number']))
        ]

    def fetch_single_row(self, sku_id: str) -> Dict:
        row = self.product_df[self.product_df['Manufacturer Model Number'].apply(lambda x: f"{self.sku_prefix}-{x}") == sku_id]
        return row.to_dict('records')[0]

    def upsert_all_anderson_data(self):        
        for idx, data in self.product_df.iterrows():
            try:
                data = data.to_dict()
                data = self.create_product_data(data)
                if data.shopifyId:
                    self.product_dao.upsert_product(data, selected_keys=[
                        "variants",
                    ], update_meta=False)
                else:
                    self.product_dao.upsert_product(data)
                print(data.productId, 'Success')
            except Exception:
                logger.error(f"Error while upsert product {traceback.format_exc()}")

    def create_cushion_data(self, orignial_data: product_data.ProductData, x: Dict) -> product_data.ProductData:  
        default_id = f"{self.sku_prefix}-{x['SKU']}"
        sku = product_data.Sku(
            skuId=default_id,
            supplierSku=x['SKU'] ,
            price=x['MAP'] + orignial_data.price,
            beforeSalePrice=x['MAP'] + orignial_data.beforeSalePrice,
            cost=x['Canvas / Waves /'] + orignial_data.cost,
        )
        sku.optionList = [product_data.OptionData(
            optionName="Cushion",
            optionValue=f"{x['Color']}",
        )]
        stock = self.parse_cushion_inventory_stock(x)
        sku.warehouseInfo = [product_data.WarehouseData(
            stock=min(stock, orignial_data.stock)
        )]
        sku.isSoldOut = stock == 0
        sku.weightInfo = orignial_data.weightInfo
        return sku

    def parse_shiptype_data(self, x: Dict) -> ShipTypeType:
        if x['Ship Type (small parcel, LTL)'] == LTL:
            return LTL
        else:
            return PARCEL

    def create_product_data(self, x: Dict) -> product_data.ProductData:  
        default_id = f"{self.sku_prefix}-{x['Manufacturer Model Number']}"
        try:
            current_data_cushions = self.cushion_price_df[
                self.cushion_price_df['cushionFor'].apply(lambda x: x.lower()) == x['Manufacturer Model Number'].lower()
            ]
            cushion_list = current_data_cushions.to_dict('records')
            product_model = self.product_dao.fetch_product(default_id)
            product_model.stock = self.parse_inventory_stock(x)
            product_model.price = x['MAP Price (Sale Price)']
            product_model.upcCode = str(int(x['UPC Code']))
            return product_model
        except NoProductError:
            pass

        product_model = product_data.ProductData(
            productId=default_id,
            upcCode=str(int(x['UPC Code'])),
            cost=x['Wholesale Price'],
            price=x['MAP Price (Sale Price)'],
            shortDescription=x.get("Paragraph description (if exist)", ""),
            tagList=[y.strip() for y in x.get('tags','').split(',') if y],
            productType='Kitchen & Dining Furniture Sets',
            trackInventory=True,
            brandName="Anderson Teak",
            taxable=True,
        )
        product_model.brandData = self.brand_data
        before_sale_price  = random.choice([100, 920, 300, 250, 500, 300, 200, 1000, 1050, 400, 450])
        product_model.beforeSalePrice = before_sale_price + product_model.price
        try:
            product_model.goodsName = self.parse_title(x)
        except Exception:
            raise ValueError(f"Error while make goods Name {product_model.productId}")

        try:
            product_model.shipType = self.parse_shiptype_data(x)
        except Exception:
            logger.error(f"Error while make shiptype {product_model.productId}")
            return None    

        try:
            product_model.mainImageList = self.parse_main_image_list(x)
        except Exception:
            raise ValueError(f"Error while make main image list {product_model.productId} {traceback.format_exc()}")

        try:
            product_model.featureList = self.parse_feature_list(x)
        except Exception:
            raise ValueError(f"Error while make features  {product_model.productId} {traceback.format_exc()} ")

        try:
            product_model.description = self.make_product_description(product_model, prop_sixty_five=True)
        except Exception:
            raise ValueError(f"Error while make descriiption {product_model.productId}")
        
        try:
            product_model.warranty = self.parse_warranty(x)
        except Exception:
            raise ValueError(f"Error while make warranty {product_model.productId}")
        
        try:
            product_model.stock = self.parse_inventory_stock(x)
        except Exception as e:
            raise ValueError(f"Error while make stock {product_model.productId} {str(e)}")

        try:
            product_model.goodsMustInfo = self.parse_must_info_list(x)
        except Exception as e:
            raise ValueError(f"Error while make goodsmust info {product_model.productId} {str(e)}")

        try:
            product_model.deliveryDataList = [self.parse_delivery_data(x)]
        except Exception:
            raise ValueError(f"Error while delivery data {product_model.productId}")

        try:
            product_model.weightInfo = self.parse_weight_info(x)
        except Exception:
            raise ValueError(f"Error while make weight info data {product_model.productId}")

        try:
            skuList = list(map(lambda x: self.create_cushion_data(product_model, x), cushion_list))
            if skuList:
                first_sku = product_data.Sku(
                    skuId=default_id,
                    supplierSku=x['Manufacturer Model Number'],
                    price=product_model.price,
                    cost=product_model.cost,
                )
                first_sku.optionList = [
                    product_data.OptionData(
                        optionName="Cushion",
                        optionValue="No Cushion",
                    )
                ]
                first_sku.warehouseInfo = [
                    product_data.WarehouseData(
                        stock=product_model.stock
                    )
                ]
                product_model.skuList = [first_sku] + skuList
                product_model.optionNameList = ["Cushion"]
                product_model.mainImageList += [
                    "https://smoothdiningbucket.s3.us-west-1.amazonaws.com/shopifyimages/andersonteakimages/newcushioncolors.jpg",
                    "https://smoothdiningbucket.s3.us-west-1.amazonaws.com/shopifyimages/andersonteakimages/new-cushion-cover.jpg"
                ]
        except Exception as e:
            raise ValueError(f"Error while sku list {product_model.productId} {str(e)}")
        try:
            product_model.productType = "Kitchen & Dining Furniture Sets"
            add_additional_tag_to_product(product_model)
        except Exception:
            raise ValueError(f"Error while make tag data")
        return product_model

    def filter_cushon_df(self, **kwargs):
        if kwargs['Manufacturer Model Number'] in self.with_cushion_list:
            return False
        for key in self.feature_column_list:
            if type(kwargs[key]) is str and self.no_cushion_message.lower() in kwargs[key].lower():
                return True
        return False

    def parse_inventory_stock(self, x: Dict) -> int:
        fiiltered_inventory = self.inventory_df[self.inventory_df['Item Number'].apply(lambda x : x.lower()) == x['Manufacturer Model Number'].lower()]
        inventory_list = list(fiiltered_inventory.iterrows())
        if not inventory_list:
            return 0
        inventory_data = dict(inventory_list[0][1])
        return inventory_data['Qty On Hand']

    def parse_cushion_inventory_stock(self, x: Dict) -> int:
        fiiltered_inventory = self.inventory_df[
            self.inventory_df['Item Number'].apply(
                lambda x : x.lower()
            ) == x['SKU'].lower().replace("cush-", '')
        ]
        fiiltered_inventory_list = list(fiiltered_inventory.iterrows())
        if not fiiltered_inventory_list:
            return 0
        inventory_data = dict(fiiltered_inventory_list[0][1])
        return inventory_data['Qty On Hand']
    
    def parse_title(self, x: Dict) -> str:
        sku = x['Manufacturer Model Number']
        product_name = x['Product Name']
        return f"Anderson Teak {product_name} {sku}"
    
    def parse_main_image_list(self, x: Dict) -> List[str]:
        default_id = f"{self.sku_prefix}-{x['Manufacturer Model Number']}"
        img_list = []
        for i in range(1, 11):
            col_name = f"Image {i} File Name"
            if check_field_exists(x[col_name]):
                img_url = parse_img_url_from_dropbox(x[col_name])
                img = upload_url_to_s3(img_url, f'/{default_id}', quality=90)
                img_list.append(img)
        return img_list

    def parse_warranty(self, x: Dict) -> str:
        warranty_header = f"<p>Warranty Period: {x['Warranty Length']}</p>"
        warranty_body = f"<p>{x['Warranty Term']}</p>"
        return f"{warranty_header}{warranty_body}{self.brand_data.warranty}"

    def parse_delivery_data(self, x: Dict) -> product_data.DeliveryData:
        min_days = (x['Supplier Lead Time in Business Day Hours'] / 24)  - 2
        max_days = (x['Supplier Lead Time in Business Day Hours'] / 24)  + 1
        return product_data.DeliveryData(
            price=0,
            cost=0,
            deliveryType=FIXED,
            minDays=min_days,
            maxDays=max_days
        )

    def parse_weight_info(self, x: Dict) -> product_data.WeightInfo:
        return product_data.WeightInfo(
            weight=x['Actual Product Weight'],
            width=x['Product Max Width'],
            height=x["Product Max Height"],
            length=x['Product Max Depth'],
            packageWeight=x['Shipping Weight (Box 1)'],
            packageWidth=x['Carton Width (Box 1)'],
            packageHeight=x['Carton Height (Box 1)'],
            packageLength=x['Carton Depth (Box 1)'],
        )

    def parse_must_info_list(self, x:Dict) -> List[product_data.MustInfo]:
        must_info_list = []
        spec_num = 1
        if check_field_exists(x["Actual Product Weight"]):
            must_info_list.append(product_data.MustInfo(
                key="Weight",
                valueList=[
                    str(x["Actual Product Weight"])
                ],

            ))
        else:
            must_info_list.append(product_data.MustInfo(
                key="Package Weight",
                valueList=[
                    str(x["Shipping Weight (Box 1)"])
                ]
            ))
            
        must_info_list.append(product_data.MustInfo(
            key="Warranty Period",
            valueList=[
                str(x["Warranty Length"])
            ]
        ))
        for i in range(1, 9):
            if check_field_exists(x[f'Specification {i}']):
                if ":" in x[f'Specification {i}']:
                    must_info_list.append(product_data.MustInfo(
                        key=x[f'Specification {i}'].split(":")[0],
                        valueList=[
                            str(x[f'Specification {i}'].split(":")[1])
                        ]
                    ))
                elif re.search(r"\d+\s*w", x[f"Specification {i}"], flags=re.IGNORECASE):
                    must_info_list.append(product_data.MustInfo(
                        key="Dimensions",
                        valueList=[
                            str(x[f'Specification {i}'])
                        ],
                        
                    ))
                else:
                    must_info_list.append(product_data.MustInfo(
                        key=f"Spec{spec_num}",
                        valueList=[
                            str(x[f'Specification {i}'])
                        ],
                        
                    ))
                    spec_num += 1     
                    

        must_info_list.append(product_data.MustInfo(
            key="Country of Manufacture",
            valueList=[
                x["Country of Manufacture"]
            ]
        ))
        must_info_list.append(product_data.MustInfo(
            key="Assembly Required? (Y/N)",
            valueList=[
                x["Assembly Required? (Y/N)"]
            ]
        ))
        return must_info_list

    def parse_feature_list(self, x: Dict) -> List[str]:
        li_list = []
        for feature_col in self.feature_column_list:
            if check_field_exists(x[feature_col]):
                li_list.append(x[feature_col])
        return li_list
