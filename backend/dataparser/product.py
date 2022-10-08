from typing import Dict, Tuple

from models.product_data import ProductData, Sku, WeightInfo, WarehouseData, OptionData
from .numbers import round_up_decimals


def product_data_to_shopify_format(product_data: ProductData, inventory_id: str = "") -> Dict:
    data_dict = {
        "title": product_data.goodsName,
        "handle": product_data.productId, 
        "descriptionHtml": product_data.shortDescription,
        "vendor": product_data.brandName,
        "productType": product_data.productType,
        "tags": product_data.tagList,
        "published": True,
    }
    variant_list = []
    option_image_list = []
    for sku in product_data.skuList:
        if sku.weightInfo and sku.weightInfo.packageWeight:
            weight = sku.weightInfo.packageWeight
        elif sku.weightInfo and sku.weightInfo.weight:
            weight = sku.weightInfo.weight
        else:
            weight = 0
        stock_sum = sum([warehouse.stock for warehouse in sku.warehouseInfo])
        base_sku_dict = {
            "sku": sku.skuId,
            "compareAtPrice": sku.beforeSalePrice,
            "price": sku.price, 
            "inventoryQuantities": [
                {
                    "availableQuantity": stock_sum,
                    "locationId": inventory_id

                }
            ],
            "weight": weight,
            "weightUnit": "POUNDS",
            "taxable": product_data.taxable
        }
        if len(base_sku_dict.get('inventoryQuantities', [])) > 0:
            base_sku_dict['inventoryManagement'] = 'SHOPIFY'
            base_sku_dict['inventoryPolicy'] = 'DENY'
        else:
            base_sku_dict['inventoryManagement'] = 'NOT_MANAGED'
            base_sku_dict['inventoryPolicy'] = 'CONTINUE'

        option_list = []
        option_image = None
        for option in sku.optionList:
            option_list.append(option.optionValue)
            option_image = option.optionImage
            if option_image not in option_image_list and option_image:
                option_image_list.append(option_image)
        if option_list:
            base_sku_dict['options'] = option_list
        if option_image:
            base_sku_dict['imageSrc'] = option_image
        variant_list.append(base_sku_dict)
    if not product_data.skuList:
        if product_data.weightInfo and product_data.weightInfo.packageWeight:
            weight = product_data.weightInfo.packageWeight
        elif product_data.weightInfo and product_data.weightInfo.weight:
            weight = product_data.weightInfo.weight
        else:
            weight = 0
        variant_list.append({
            "sku": product_data.productId,
            "compareAtPrice": product_data.beforeSalePrice,
            "price": product_data.price,
            "inventoryManagement": "NOT_MANAGED",
            "inventoryPolicy": "CONTINUE",
            "weight": weight, 
            "weightUnit": "POUNDS",
            "taxable": product_data.taxable
        })
        if product_data.trackInventory:
            variant_list[-1]["inventoryManagement"] = "SHOPIFY"
            variant_list[-1]["inventoryPolicy"] = "DENY"
            variant_list[-1]['inventoryQuantities'] = {
                "availableQuantity": product_data.stock, 
                "locationId": inventory_id
            }
            
            
    if product_data.shopifyId:
        data_dict['id'] = product_data.shopifyId
    data_dict['variants'] = variant_list
    if product_data.optionNameList:
        data_dict['options'] = product_data.optionNameList
    data_dict['images'] = [
        {"src": x}
        for x in product_data.mainImageList + option_image_list
    ]
    return data_dict

def calculate_review_average(product_data: ProductData) -> float:
    if not product_data.reviewList:
        return 0.0
    return round_up_decimals(
        sum([review_data.reviewPoint for review_data in product_data.reviewList]) / len(product_data.reviewList), 
        1
    )


def calculate_sales_percentage(product_data: ProductData) -> float:
    if not product_data.skuList:
        return 0.0
    first_sku = product_data.skuList[0]
    if float(first_sku.beforeSalePrice) == 0:
        return 0.0
    return round_up_decimals(
        (float(first_sku.beforeSalePrice) - float(first_sku.price)) / float(first_sku.beforeSalePrice) * 100,
        2
    )


def shopify_data_to_product_data(shopify_data: Dict) -> ProductData:
    product_data = ProductData(
        goodsName=shopify_data.get('title'),
        productId=shopify_data.get('handle'),
        shortDescription=shopify_data.get('descriptionHtml'),
        brandName=shopify_data.get('vendor'),
        productType=shopify_data.get('productType', ''),
        tags=shopify_data.get('tags', []),
        published=True,
        shopifyId=shopify_data.get('id', '')
    )
    image_list = [x['node']['url'] for x in shopify_data.get('images', {}).get('edges', [])]
    product_data.mainImageList = image_list
    video_url_list = [
        x['node']['originalSource']['url'] for x in shopify_data.get('media', {}).get('edges', [])
        if x.get('node') and x.get('node', {}).get('id')
    ]
    for node in shopify_data['metafields'].get('edges', []):
        metadata = node.get('node')
        if metadata.get('key') == 'description':
            product_data.description = metadata.get('value')
        if metadata.get('key') == 'ingredient':
            product_data.ingredient = metadata.get('value')
        if metadata.get('key') == 'manual':
            product_data.manual = metadata.get('value')
        if metadata.get('key') == 'warranty':
            product_data.warranty = metadata.get('value')
            
    product_data.videoUrlList = video_url_list
    sku_list = []
    for node in shopify_data.get('variants', {}).get('edges', []):
        vdata = node.get('node')
        warehouse_data = WarehouseData(
            stock=vdata.get('inventoryQuantity')
        )
        sku = Sku(
            skuId=vdata.get('sku'),
            shopifyId=vdata.get('id'),
            price=float(vdata.get('price')),
            cost=float(vdata.get('inventoryItem', {}).get('unitCost', {}).get('amount', 0.0)),
            beforeSalePrice=float(vdata.get('compareAtPrice')),
        )
        weight_info_list = WeightInfo(
            weight=vdata.get('weight', 0.0)
        )
        opt_image = vdata.get('image').get('url') if vdata.get('image') else None
        option_list = []
        for opt in  vdata.get("options", []):
            od = OptionData(
                optionName=opt.get('name'),
                optionValue=opt.get('value'),
                optionImage=opt_image,
            )
            option_list.append(od)
        sku.warehouseInfo = [warehouse_data]
        sku.weightInfo = weight_info_list
        sku.optionList = option_list
        sku_list.append(sku)
    product_data.skuList = sku_list
    return product_data