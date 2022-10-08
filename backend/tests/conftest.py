import pytest

from shopify_dao.shop_app import create_shopify_app
from shopify_dao.product import ProductDao
from models.product_data import BrandData
from pymongo import MongoClient
from pymongo.database import Database
from config import TestConfig
from shopify.resources.shop import Shop
from application import create_app


@pytest.fixture(scope="session")
def test_app():
    # set up

    app = create_app('config.TestConfig')
    with app.app_context():
        client = app.test_client()
        yield client


@pytest.fixture(scope="session")
def mongodb() -> Database:
    client = MongoClient(TestConfig.MONGO_URI)
    db = client[TestConfig.DB_NAME]
    yield db
    client.drop_database(TestConfig.DB_NAME)
    client.close()


@pytest.fixture(scope="session")
def product_dao(mongodb) -> ProductDao:
    shop = create_shopify_app()
    product_dao = ProductDao(shop, mongodb)
    yield product_dao


@pytest.fixture(scope="session")
def shop() -> Shop:
    shop = create_shopify_app()
    yield shop


@pytest.fixture(scope="session")
def brand_data() -> BrandData:
    with open("supplier_manager/andersonteak/warranty.html") as f:
        brand_data = BrandData(
            brandName="ACME Furniture",
            warranty=f.read(),
        )    
    yield brand_data
