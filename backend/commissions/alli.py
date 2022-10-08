from models.product_data import ProductData
from dataparser.numbers import round_up_decimals


def convert_alli_commissions(product_data: ProductData, commission=1.3) -> ProductData:
    delivery_price = product_data.deliveryDataList[0].cost
    price = (delivery_price + product_data.cost) * commission
    product_data.price = round_up_decimals(price, decimals=2)
    for sku in product_data.skuList:
        price = (delivery_price + sku.cost) * commission
        before_sale_price = (delivery_price + sku.beforeSalePrice) * commission
        sku.price = round_up_decimals(price, decimals=2)
        sku.beforeSalePrice =  round_up_decimals(before_sale_price, decimals=2)
    return product_data