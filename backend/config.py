from pathlib import Path  # python3 only
import os
from dotenv import load_dotenv


env_path = Path('./envfiles/.shopifysecret.env')
mongo_env_path = Path('./envfiles/.mongodb.env')
aws_secret_path = Path('./envfiles/aws.secret.env')
service_path = Path('./envfiles/.service.env')


load_dotenv(dotenv_path=env_path)
load_dotenv(dotenv_path=mongo_env_path)
load_dotenv(dotenv_path=aws_secret_path)
load_dotenv(dotenv_path=service_path)

class BaseConfig:
    BASE_SHOP_URL: str = f"{os.environ.get('SHOP_NAME')}.myshopify.com/admin"
    SHOP_PASS:str = os.environ.get('SHOP_APP_PASSWORD')
    SHOP_KEY:str = os.environ.get('SHOP_API_KEY')
    SHOP_FULL_URL = f"https://{os.environ.get('SHOP_API_KEY')}:{os.environ.get('SHOP_APP_PASSWORD')}@{os.environ.get('SHOP_NAME')}.myshopify.com/admin"
    API_VERSION: str = '2022-01'
    MONGO_URI: str = os.environ.get("MONGO_URI")
    SECRET_KEY: str = "flasksecretasdlkfjsd"
    BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
    S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY_ID")
    S3_ACCESS_SECRET = os.environ.get("S3_ACCESS_SECRET_KEY")
    CLOUDRUN_API_URL = os.environ.get("CLOUDRUN_API_URL")
    S3_REGION = 'us-west-1'
    CKEDITOR_FILE_UPLOADER = '/upload'
    CKEDITOR_EXTRA_PLUGINS = ['filebrowser']
    CKEDITOR_FILE_BROWSER = '/upload'
    CKEDITOR_PKG_TYPE = "full-all"



class TestConfig(BaseConfig):
    DB_NAME: str = "testdb"
    MONGODB_NAME: str = "testdb"


class ProductionConfig(BaseConfig):
    DB_NAME: str = "shopify"
    MONGODB_NAME: str = "shopify"
    DEBUG: bool = True
    TESTING: bool = True
    ENV: str = 'development'