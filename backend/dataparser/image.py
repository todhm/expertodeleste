from typing import Dict, Literal, Tuple, Optional, List
from io import BytesIO
import asyncio
import os
import shutil

from PIL import Image
from pygifsicle import gifsicle
import requests
from botocore.client import Config
import boto3
import aiohttp
from aiobotocore.session import get_session

from .strings import random_string
from config import ProductionConfig


def create_s3():
    ACCESS_KEY_ID = ProductionConfig.S3_ACCESS_KEY
    ACCESS_SECRET_KEY = ProductionConfig.S3_ACCESS_SECRET
    s3 = boto3.resource(
        's3',
        aws_access_key_id=ACCESS_KEY_ID,
        aws_secret_access_key=ACCESS_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name=ProductionConfig.S3_REGION
    )
    return s3


def create_image_file(imgf: str) -> Dict:
    image = Image.open(imgf).convert('RGB')
    fname = random_string(5)
    fname = f"{fname}.jpg"
    image.save(fname, format='JPEG', optimize=True)
    return  {
        "filename": fname,
        "mimeType": "image/jpg",
        "resource": "IMAGE",
      }


def create_s3_url(
    imgf: BytesIO, extension: Literal['jpg', 'gif', 'png', 'jpeg', "png", "pdf"], folder_prefix: str = "", 
    quality: int = 100,
    resize_tuple: Optional[Tuple] = None,
    fix_image_width: Optional[int] = None
) -> Dict:
    BUCKET_NAME = ProductionConfig.BUCKET_NAME
    fname = random_string(5)
    fname = f"{fname}.{extension}"
    s3 = create_s3()
    if extension == "pdf":
        result = s3.meta.client.upload_file(imgf, 'mybucket', imgf.split('/')[-1])
        return result
    in_mem_file = BytesIO()
    image = Image.open(imgf).convert('RGB')
    if resize_tuple:
        image = image.resize(resize_tuple)
    if fix_image_width:
        i_width = image.size[0]
        i_height = image.size[1]
        if int(i_width) > fix_image_width:
            f_resize_width = fix_image_width / float(i_width)
            i_resize_height = int((float(i_height) * float(f_resize_width)))
            image = image.resize((fix_image_width, i_resize_height), Image.ANTIALIAS)
    image.save(in_mem_file, format='JPEG', optimize=True, quality=quality)
    data = in_mem_file.getvalue()
    full_file_name = f"shopifyimages{folder_prefix}/" + fname
    s3.Bucket(BUCKET_NAME).put_object(Key=full_file_name, Body=data, ACL='public-read', ContentType='image/jpeg')
    in_mem_file.seek(0)
    server_url = f"https://{BUCKET_NAME}.s3.us-west-1.amazonaws.com/{full_file_name}"
    return  server_url

class ImageDao(object):


    def __init__(
        self,
        resize_tuple: Optional[Tuple] = None,
        fix_image_width: Optional[int] = None,
        quality: float = 100.0,
    ):
        self.resize_tuple = resize_tuple
        self.fix_image_width = fix_image_width
        self.quality = quality

    def rebuild_image(
        self,
        image: Image.Image
    ) -> Image.Image:
        if self.resize_tuple:
            image = self.resize_image(image)
        if self.fix_image_width:
            image = self.make_fix_with_image(image)
        return image

    def resize_image(
        self,
        image: Image.Image,
    ) -> Image.Image:
        image = image.resize(self.resize_tuple)
        return image


    def make_fix_with_image(
        self,
        image: Image.Image,
    ) -> Image.Image:
        i_width = image.size[0]
        i_height = image.size[1]
        if int(i_width) > self.fix_image_width:
            f_resize_width = self.fix_image_width / float(i_width)
            i_resize_height = int((float(i_height) * float(f_resize_width)))
            image = image.resize((self.fix_image_width, i_resize_height), Image.ANTIALIAS)
        return image

    def save_gif(
        self,
        imagef: BytesIO,
    ) -> BytesIO:
        temp_input_fname = "temp.gif"
        source = "sourcetemp.gif"
        with open(temp_input_fname, "wb") as f:
            shutil.copyfileobj(imagef, f)
        gifsicle(
            sources=temp_input_fname,
            destination=source,
            optimize=True, # Whetever to add the optimize flag of not
            options=["--verbose"] # Options to use.
        )
        with open(source, 'rb') as f:
            output =  BytesIO(f.read())
        os.remove(temp_input_fname)
        os.remove(source)
        return output
    
    def save_image(
        self,
        image: Image.Image,
        output: str, 
    )-> Image.Image:
        image = image.convert('RGB')
        image = self.rebuild_image(image)
        image.save(output, format='JPEG', optimize=True, quality=self.quality)
        return image


def upload_url_to_s3(
    url: str,
    folder_prefix: str = "",
    quality: float = 100,
    resize_tuple: Optional[Tuple] = None,
    fix_image_width: Optional[int] = None
) -> str:
    response = requests.get(url,stream= True)
    f = BytesIO(response.content)
    s3_url = create_s3_url(f, 'jpg', folder_prefix=folder_prefix, quality=quality, resize_tuple=resize_tuple, fix_image_width=fix_image_width)
    return s3_url


async def upload_s3_object(
    client,
    imgf: BytesIO, extension: Literal['jpg', 'gif', 'png', 'jpeg', "png"], folder_prefix: str = "", 
    quality: int = 100,
    resize_tuple: Optional[Tuple] = None,
    fix_image_width: Optional[int] = None,
    original_image_url: Optional[str] = None
):
    BUCKET_NAME = ProductionConfig.BUCKET_NAME
    fname = random_string(5)
    fname = f"{fname}.{extension}"
    in_mem_file = BytesIO()
    try:
        image = Image.open(imgf).convert('RGB')
        if resize_tuple:
            image = image.resize(resize_tuple)
        if fix_image_width:
            i_width = image.size[0]
            i_height = image.size[1]
            if int(i_width) > fix_image_width:
                f_resize_width = fix_image_width / float(i_width)
                i_resize_height = int((float(i_height) * float(f_resize_width)))
                image = image.resize((fix_image_width, i_resize_height), Image.ANTIALIAS)
        image.save(in_mem_file, format='JPEG', optimize=True, quality=quality)
        data = in_mem_file.getvalue()
        full_file_name = f"shopifyimages{folder_prefix}/" + fname
        await client.put_object(Bucket=BUCKET_NAME, Key=full_file_name, Body=data, ACL='public-read', ContentType='image/jpeg')
        in_mem_file.seek(0)
        server_url = f"https://{BUCKET_NAME}.s3.us-west-1.amazonaws.com/{full_file_name}"
        return server_url
    except Exception:
        raise ValueError(f"Error while convert image url {original_image_url}")


async def load_bytesio(imageurl):
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(imageurl) as resp:
            try:
                result_bytes = await resp.read()
                bytes_io = BytesIO(result_bytes)
                return bytes_io
            except Exception:
                raise ValueError(f"Error while fetching this image {imageurl}")


async def upload_urls_to_s3_list(
    url_list: List[str],
    folder_prefix: str = "",
    quality: float = 100,
    resize_tuple: Optional[Tuple] = None,
    fix_image_width: Optional[int] = None
) -> List[str]:
    ACCESS_KEY_ID = ProductionConfig.S3_ACCESS_KEY
    ACCESS_SECRET_KEY = ProductionConfig.S3_ACCESS_SECRET
    call_image_list =  [load_bytesio(url) for url in url_list]
    bytes_io_list = await asyncio.gather(*call_image_list)
    # bytes_io_list = [bytedata for bytedata in bytes_io_list if not isinstance(bytedata, Exception)]
    if not bytes_io_list:
        raise ValueError("No image data made")
    session = get_session()
    async with session.create_client(
        's3', 
        aws_secret_access_key=ACCESS_SECRET_KEY,
        aws_access_key_id=ACCESS_KEY_ID
    ) as client:
        result_list = [upload_s3_object(
            client,
            x,
            'jpg',
            folder_prefix=folder_prefix,
            quality=quality,
            resize_tuple=resize_tuple,
            fix_image_width=fix_image_width,
            original_image_url=url_list[idx]
        ) for idx, x in enumerate(bytes_io_list)]

        return await asyncio.gather(*result_list)