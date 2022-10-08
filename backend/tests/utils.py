from typing import List, Dict
from models.product_data import ProductData


def assert_set_data(
    data: ProductData, 
    default_set_length: int = 0, 
    additional_set_length: int = 0, 
    key_exists_pairs: List[Dict] = [],
    tag_check_list: List[str] = [],
    sku_length: int = 0
):
    assert len(data.mainImageList) > 0
    assert len(data.goodsName) > 0
    assert len(data.goodsMustInfo) > 0

    assert len(data.productId) > 0

    assert len(data.defaultSetList) == default_set_length
    assert len(data.additionalProductList) == additional_set_length
    assert len(data.skuList) == sku_length
    
    for sku in data.skuList:
        assert sku.price > 0
        assert sku.beforeSalePrice > 0
        assert sku.cost > 0
        assert sku.beforeSalePrice >= sku.price

        for option_data, option_name in zip(sku.optionList, data.optionNameList):
            assert option_name == option_data.optionName

    for default_set in data.defaultSetList:
        assert default_set.defaultCount > 0
        assert len(default_set.thumbnailImage) > 0
        assert len(default_set.productName) > 0
    for additional_product in data.additionalProductList:
        assert len(additional_product.productName) > 0
        assert len(additional_product.thumbnailImage) > 0
        assert additional_product.beforeSalePrice > 0
        assert additional_product.price > 0

    for goods_must_info in data.goodsMustInfo:
            for key_regex_data in key_exists_pairs:
                if key_regex_data['key'] in goods_must_info.key:
                    key_regex_data['exists'] = True
    assert all([x['exists'] for x in key_exists_pairs])
    for tag in tag_check_list:
        assert tag in data.tagList