from typing import List

from models.product_data import ProductData, Sku, WeightInfo
from models.google_merchant_data import GoogleProductType
from data_types.google_category import DINING_TABLE_CATEGORY_ID
from data_types.shipping import FIXED
from data_types import brand_types
from data_types.google_merchant_labels import LTL, FREE
from dataparser.excel_data import check_field_exists
from dataparser.numbers import round_up_decimals



class GoogleMerchantParser(object):

    @classmethod
    def parse_basic_part(
        cls, gpd: GoogleProductType,
        product_data: ProductData, 
        weight_info_list: List[WeightInfo],
        weight_info: WeightInfo
    ) -> GoogleProductType:
        gpd["additional_image_link"] = ','.join(product_data.mainImageList[1:])
        product_feature_list = []
        for x in product_data.featureList:
            x = x.replace(",", '')
            if len(','.join(product_feature_list) + x) < 150:
                product_feature_list.append(x)
            else:
                break
        gpd["product_highlight"] = ','.join(product_feature_list)
        delivery_data = product_data.deliveryDataList[0]
        fixed_delivery = delivery_data.deliveryType == FIXED
        if fixed_delivery:
            if delivery_data.price == 0:
                gpd["shippnig_label"] = FREE
            gpd[
                "shipping(country:price:min_handling_time:max_handling_time:min_transit_time:max_transit_time)"
            ] = (
                "US:"
                f"{delivery_data.price} USD:"
                "1:"
                "3:"
                f"{delivery_data.minDays}:"
                f"{delivery_data.minDays + 2}"
            )
        else:
            gpd["shipping(country:price:min_handling_time:max_handling_time:min_transit_time:max_transit_time)"] = ""
            if product_data.shipType == LTL:
                gpd["shipping_label"] = product_data.shipType
            else:
                if product_data.brandName in [brand_types.WINSOME, brand_types.ACME_FURNITURE, brand_types.MANHATTAAN_COMFORT]:
                    gpd['shipping_label'] = product_data.brandName
        if weight_info_list:
            total_shipping_weight = sum([x.packageWeight for x in weight_info_list])
            total_product_weight = sum([x.weight for x in weight_info_list])
        else:
            total_shipping_weight = weight_info.packageWeight
            total_product_weight = weight_info.weight

        if check_field_exists(total_shipping_weight):
            gpd["shipping_weight"] = f"{total_shipping_weight} lb"

        if check_field_exists(total_product_weight):
            gpd["product_weight"] = f"{total_shipping_weight} lb"

        kevalue_list = [
            (weight_info.packageLength, "shipping_length"),
            (weight_info.packageWidth, "shipping_width"),
            (weight_info.packageHeight, "shipping_height"),
            (weight_info.length, "product_length"),
            (weight_info.width, "product_width"),
            (weight_info.height, "product_height"),
        ]
        for value, key in kevalue_list:
            if check_field_exists(value):
                value = round_up_decimals(value, 2)
                gpd[key] = f"{value} in"
        gpd["product_detail(attribute_name:attribute_value)"] = ','.join([f"{must_info.key}:{' '.join([str(x).replace(',', ' ') for x in must_info.valueList])}" for must_info in product_data.goodsMustInfo])
        gpd["availability"] = "in_stock" if product_data.stock > 0 else "out_of_stock"
        return gpd

    @classmethod
    def parse_product_data(cls, product_data: ProductData) -> List[GoogleProductType]:
        if not product_data.skuList or product_data.brandName == brand_types.ANDERSON_TEAK:
            gpd = GoogleProductType(
                id=product_data.productId,
                title=product_data.goodsName,
                description=product_data.shortDescription,
                cost_of_goods_sold=f"{product_data.cost} USD",
                link=f"https://smoothdining.com/products/{product_data.productId}",
                condition="new",
                price=f"{product_data.price} USD",
                image_link=product_data.mainImageList[0],
                brand=product_data.brandName,
                google_product_category=DINING_TABLE_CATEGORY_ID,
                item_group_id=product_data.productId,
                ships_from_country="US",
                min_handling_time=1,
                max_handling_time=3,
                product_type=product_data.productType
            )
            if product_data.upcCode:
                gpd["gtin"] = product_data.upcCode
            gpd = cls.parse_basic_part(gpd, product_data, product_data.weightInfoList, product_data.weightInfo)
            return [gpd]
        else:
            gpd_list = list(map(lambda x: cls.parse_sku_data(product_data, x) , product_data.skuList))
            return gpd_list

    @classmethod
    def parse_sku_data(cls, product_data: ProductData, sku: Sku) -> GoogleProductType:
        gpd = GoogleProductType(
            id=sku.skuId,
            title=product_data.goodsName,
            description=product_data.shortDescription,
            cost_of_goods_sold=f"{product_data.cost} USD",
            link=f"https://smoothdining.com/products/{product_data.productId}",
            condition="new",
            price=f"{product_data.price} USD",
            image_link=product_data.mainImageList[0],
            brand=product_data.brandName,
            google_product_category=DINING_TABLE_CATEGORY_ID,
            item_group_id=product_data.productId,
            ships_from_country="US",
            min_handling_time=1,
            max_handling_time=3,
        )
        if sku.upcCode:
            gpd['gtin'] = sku.upcCode
        weight_info_list = sku.weightInfoList if sku.weightInfoList else product_data.weightInfoList
        weight_info = sku.weightInfo if sku.weightInfo else product_data.weightInfo
        gpd = cls.parse_basic_part(gpd, product_data, weight_info_list, weight_info)
        if sku.warehouseInfo:
            gpd["availability"] = "in_stock" if sku.warehouseInfo[0].stock > 0 else "out_of_stock"
        return gpd