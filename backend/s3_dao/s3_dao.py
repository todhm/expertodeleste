from typing import Dict, Literal, Tuple, Optional
from io import BytesIO

from PIL import Image
from flask import current_app
from werkzeug.datastructures import FileStorage
import boto3
from aiobotocore.session import get_session
from botocore.client import Config

from dataparser.strings import random_string
from dataparser.image import ImageDao



class S3_Dao(object):


    def __init__(self):
        self.ACCESS_KEY_ID = current_app.config['S3_ACCESS_KEY']
        self.ACCESS_SECRET_KEY = current_app.config['S3_ACCESS_SECRET']
        self.S3_REGION = current_app.config['S3_REGION']
        self.S3_BUCKET_NAME = current_app.config['BUCKET_NAME']

        self.session = get_session()
        self.s3 = boto3.resource(
            's3',
            aws_access_key_id=self.ACCESS_KEY_ID,
            aws_secret_access_key=self.ACCESS_SECRET_KEY,
            config=Config(signature_version='s3v4'),
            region_name=self.S3_REGION
        )

    async def __aenter__(self):
        async with self.session.create_client(
            's3', 
            aws_secret_access_key=self.ACCESS_SECRET_KEY,
            aws_access_key_id=self.ACCESS_KEY_ID
        ) as client:
            self.client = client
            return self

    def upload_data_from_file(
        self,
        f: FileStorage,
        folder_prefix: str = "",
        quality: int = 100,
        resize_tuple: Optional[Tuple] = None,
        fix_image_width: Optional[int] = None
    ) -> str:
        extension = f.filename.split('.')[-1].lower()
        if extension not in ['jpg', 'gif', 'png', 'jpeg']:
            raise ValueError("Image Only!")
        return self.upload_file(
            f,
            extension,
            folder_prefix=folder_prefix,
            quality=quality,
            resize_tuple=resize_tuple,
            fix_image_width=fix_image_width
        )
    
    def upload_file(
        self,
        imgf: BytesIO, 
        extension: Literal['jpg', 'gif', 'png', 'jpeg', "png", "pdf"],
        folder_prefix: str = "", 
        quality: int = 100,
        resize_tuple: Optional[Tuple] = None,
        fix_image_width: Optional[int] = None
    ) -> str:
        fname = random_string(5)
        fname = f"{fname}.{extension}"
        if extension == "pdf":
            result = self.s3.meta.client.upload_file(imgf, 'mybucket', imgf.split('/')[-1])
            return result
        imd = ImageDao(
            resize_tuple=resize_tuple,
            fix_image_width=fix_image_width,
            quality=quality
        )
        in_mem_file = BytesIO()
        if extension == 'gif':
            in_mem_file = imd.save_gif(imgf)
        else:
            image = Image.open(imgf)
            image = imd.save_image(image, in_mem_file)
        data = in_mem_file.getvalue()
        full_file_name = f"shopifyimages{folder_prefix}/" + fname
        self.s3.Bucket(self.S3_BUCKET_NAME).put_object(Key=full_file_name, Body=data, ACL='public-read', ContentType='image/jpeg')
        in_mem_file.seek(0)
        server_url = f"https://{self.S3_BUCKET_NAME}.s3.us-west-1.amazonaws.com/{full_file_name}"
        return  server_url
        
