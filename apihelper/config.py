from pathlib import Path  # python3 only
import os
from dotenv import load_dotenv


fedex_env = Path('./envfiles/.fedex.env')


load_dotenv(dotenv_path=fedex_env)


class BaseConfig:
    API_VERSION: str = '2022-01'
    

class DevelopmentConfig(BaseConfig):
    DB_NAME: str = "testdb"
    MONGODB_NAME: str = "testdb"
    TESTING: bool = True
    DEBUG: bool = True
    ENV: str = 'development'
    FEDEX_URL: str = os.environ.get("TEST_URL")
    FEDEX_CLIENT_ID: str = os.environ.get("TEST_CLIENT_ID")
    FEDEX_CLIENT_SECRET: str = os.environ.get("TEST_CLIENT_SECRET")
    FEDEX_LTL_ACCOUNT: str = os.environ.get("TEST_LTL_ACCOUNT")
    FEDEX_NONE_LTL_ACCOUNT: str = os.environ.get("TEST_NONE_LTL_ACCOUNT")


class ProductionConfig(BaseConfig):
    DB_NAME: str = "shopify"
    MONGODB_NAME: str = "shopify"
    TESTING: bool = False
    DEBUG: bool = False
    ENV: str = 'production'