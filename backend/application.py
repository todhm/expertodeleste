from flask import Flask
from flask_admin import Admin
from mongoengine import connect
from flask_ckeditor import CKEditor

from models.mongo_models.product_data import Product, BrandDataCollection
from models.mongo_models.collections import Collections
from admin.product import ProductView, BrandCollectionView
from admin.brand_collection_template import BrandCollectionTemplateView
from admin.description_template import DescriptionTemplateView, DescriptionNewTemplateView
from admin.collections import CollectionsView
from scripts.brands import brand_cli
from scripts.products import product_cli
from scripts.crawl import crawl_cli
from scripts.supplier import supplier_cli
from scripts.intuitive import intuitive_cli
from scripts.fix import fix_cli
from scripts.google_merchant import google_cli
from admin.api import admin_blueprint

ckeditor = CKEditor()


def create_app(config_object='config.ProductionConfig', **config_overrides):
    # instantiate the app
    app = Flask("shopify", template_folder="templates", root_path='./')
    admin = Admin()
    ckeditor.init_app(app)
    admin.init_app(app)
    # set config
    app.config.from_object(config_object)
    app.config.update(config_overrides)
    connect(
        host=app.config.get('MONGO_URI'),
        db=app.config.get('MONGODB_NAME')
    )

    # set up extensions
    admin.add_view(ProductView(Product, name='product'))
    admin.add_view(CollectionsView(Collections, name='collectiions'))
    admin.add_view(BrandCollectionView(BrandDataCollection, name='brand collection'))
    admin.add_view(BrandCollectionTemplateView(BrandDataCollection, name='brand collection template', endpoint='template'))
    admin.add_view(DescriptionTemplateView(Product, name='description template', endpoint='descriptiontemplate'))
    admin.add_view(DescriptionNewTemplateView(Product, name='description template v2', endpoint='descriptiontemplatev2'))
    app.register_blueprint(admin_blueprint)
    app.cli.add_command(brand_cli)
    app.cli.add_command(product_cli)
    app.cli.add_command(crawl_cli)
    app.cli.add_command(supplier_cli)
    app.cli.add_command(intuitive_cli)
    app.cli.add_command(fix_cli)
    app.cli.add_command(google_cli)
    return app
