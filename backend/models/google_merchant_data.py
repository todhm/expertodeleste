from typing import TypedDict, Literal


GoogleProductType = TypedDict('RandomAlphabet', {
    "id": str, 
    "title": str,
    "description": str,
    "link": str,
    "condition": Literal["new", "refurbished", "used"],
    "price": float,
    "availability": Literal['in_stock', "out_of_stock", "preorder", "backorder"],
    "image_link": str,
    "additional_image_link": str,
    "gtin": str, 
    "mpn": str,
    "brand": str,
    "google_product_category": str, 
    "item_group_id": str,
    "sale_price": str, 
    "product_type": str, 
    "color": str,
    "size": str,
    "product_length": str, 
    "product_height": str,
    "product_width": str,
    "product_weight": str,
    "product_detail(attribute_name:attribute_value)": str,
    "product_highlight": str, 
    "cost_of_goods_sold": str,
    "shipping(country:price:min_handling_time:max_handling_time:min_transit_time:max_transit_time)": str,
    "shipping_label": str, 
    "shipping_weight": str, 
    "shipping_length": str,
    "shipping_width": str,
    "shipping_height": str,
    "ships_from_country": str,
    "transit_time_label": str,
    "max_handling_time": str,
    "min_handling_time": str,
})
