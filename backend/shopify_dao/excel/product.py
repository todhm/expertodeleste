from typing import Literal, List, Dict
import copy 
from models.product_data import ProductData


def make_specification_html(product_data: ProductData) -> str:
    row_strings = ""
    for must_info in product_data.goodsMustInfo:
        value_p_list = ''.join([f"<p>{value}</p>" for value in must_info.valueList])
        row_strings += f"<tr><td>{must_info.key}</td><td>{value_p_list}</td></tr>"
    html_string = f'<table width="100%"><tbody>{row_strings}</tbody></table>'
    return html_string


def make_delivery_html(product_data: ProductData) -> str:
    header_string: str = '''
        <thead>
          <tr>
            <th scope="col">Delivery Methods</th>
            <th scope="col">Estimated Delivery Time</th>
            <th scope="col">Delivery Price</th>
          </tr>
        </thead>
    '''
    row_strings = ""
    for delivery_info in product_data.deliveryDataList:
        if delivery_info.minDays < delivery_info.maxDays:
            delivery_day_strings = f'{delivery_info.minDays} ~ {delivery_info.maxDays} Business Days'
        else:
            delivery_day_strings = f'{delivery_info.minDays} Business Days'
            
        row_strings += f"<tr><td>{delivery_info.deliveryName}</td><td>{delivery_day_strings}</td><td>{delivery_info.price} USD</td></tr>"
    html_string = f'<table width="100%">{header_string}<tbody>{row_strings}</tbody></table>'
    return html_string


def make_shopify_description(product_data: ProductData) -> str:
    header_html = '''
    <ul class="tabs">
        <li><a class="active" href="#tab1">Description</a></li>
        <li><a href="#tab2">Specs</a></li>
        <li><a href="#tab3">Brand</a></li>
        <li><a href="#tab4">Shipping</a></li>
    </ul>'''
    description_part = f'''
    <li class="active" id="tab1">
        {product_data.description}
    </li>
    '''
    specification_part = f'''
        <li class="active" id="tab2">
        {make_specification_html(product_data)}
        </li>
    '''
    brand_part = f'''
        <li class="active" id="tab3">
            <div class="spr-container">
                <div class="spr-header">
                    <img src="{product_data.brandData.brandLogo}">
                </div>
                <div class="spr-content">{product_data.brandData.brandDescription}</div>
            </div>
        </li>
    '''
    delivery_part = f'''
    <li class="active" id="tab4">
        {make_delivery_html(product_data)}
    </li>
    '''
    content_html = f'''
    <ul class="tabs-content">
        {description_part}
        {specification_part}
        {brand_part}
        {delivery_part}
    </ul>'''
    return header_html + content_html


def product_data_to_shopify_csv_format(
    pd: ProductData,
    google_product_category: str = "6347",
    gender: str = "Unisex",
    google_age_group = "Adult",
    google_adwords_group: str = "Dining Sets"
) -> List[Dict]:
    sku_dict_list = []
    base_obj_format = {
        "Handle": pd.productId,
        "Title": pd.goodsName

    }
    for sku in pd.skuList:
        sku_dict = copy.deepcopy(base_obj_format)
        sku_dict.update({
            "Variant Requires Shipping": True,
            'Variant Fulfillment Service': "manual",
            "Variant Inventory Policy": "deny",
            "Variant Taxable": True,
            "Status": "active",
            "Variant SKU": sku.skuId,



        })
        for idx, option_data in enumerate(sku.optionList):
            sku_dict[f"Option{idx + 1} Name"] = option_data.optionName
            sku_dict[f"Option{idx + 1} Value"] = option_data.optionValue
            if option_data.optionImage:
                sku_dict["Variant Image"] = option_data.optionImage
                
        for warehouse in sku.warehouseInfo:
            if warehouse.stock:
                sku_dict['Variant Inventory Qty'] = warehouse.stock
        sku_dict['Variant Compare At Price'] = sku.beforeSalePrice
        sku_dict['Variant Price'] = sku.price
        sku_dict_list.append(sku_dict)
    sku_dict_list[0]['Body (HTML)'] = make_shopify_description(pd)
    sku_dict_list[0]['SEO Description'] = pd.description
    sku_dict_list[0]['Vendor'] = pd.brandName
    sku_dict_list[0]['Tags'] = ', '.join(pd.tagList)
    sku_dict_list[0]['Published'] = True
    sku_dict_list[0]['Image Src'] = pd.mainImageList[0]
    sku_dict_list[0]['Image Position'] = 1
    sku_dict_list[0]['Google Shopping / Google Product Category'] = google_product_category
    sku_dict_list[0]['Google Shopping / Gender'] = gender
    sku_dict_list[0]['Google Shopping / Age Group'] = google_age_group
    sku_dict_list[0]['Google Shopping / AdWords Grouping'] = google_adwords_group
    sku_dict_list[0]['Google Shopping / AdWords Labels'] = ", ".join(pd.tagList)
    main_image_list_dict = []
    for idx, img in enumerate(pd.mainImageList[1:]):
        image_dict = copy.deepcopy(base_obj_format)
        image_dict['Image Src'] = img
        image_dict['Image Position'] = idx + 2
        main_image_list_dict.append(image_dict)
    return [sku_dict_list[0]] + main_image_list_dict + sku_dict_list[1:]


def product_data_to_review_format(
    pd: ProductData,
    state: Literal["published", "active"] = "published"
) -> List[Dict]:
    review_dict_data_list = []
    for review_data in pd.reviewList:
        review_dict_data_list.append({
            "product_handle": pd.productId,
            "state": state,
            "rating": review_data.reviewPoint,
            "title": review_data.reviewTitle,
            "body": review_data.reviewText,
            "author": review_data.writer,
            "created_at": review_data.reviewTime,
            "email": "contact@cozycoala.com"
        })
    return review_dict_data_list
