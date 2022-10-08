from flask_admin.contrib.mongoengine import (
    ModelView,
)
from mongoengine import get_db

from shopify_dao.product import ProductDao
from shopify_dao.shop_app import create_shopify_app
from models.product_data import ProductData


class ProductView(ModelView):
    column_default_sort = ('_id', True)
    column_filters = ('productId', 'shopifyId', 'goodsName', 'brandName', "shipType", 'stock')
    create_template = 'edit.html'
    edit_template = 'edit.html'
    column_list = ('goodsUrl', 'productId', 'shopifyId', 'goodsName')

    def on_model_change(self, form, model, is_created):
        product_data = ProductData(**model.to_json)
        if product_data.shopifyId:
            db = get_db()
            shop = create_shopify_app()
            product_dao = ProductDao(shop, db)
            product_dao.update_shopify_data(product_data)


class BrandCollectionView(ModelView):

    column_list = ('brandName', 'brandLogo')
    column_filters = ('brandName',)

    create_template = 'brandedit.html'
    edit_template = 'brandedit.html'