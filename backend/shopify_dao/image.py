import json
from typing import Dict
import os

import shopify
from shopify.resources.shop import Shop
from pymongo.database import Database

from graphqlqueries.image import UPLOAD_IMAGE_QUERY
from dataparser.image import create_image_file


class ImageDao(object):


    def __init__(self, shop: Shop, db: Database):
        self.shop = shop
        self.db = db


    def upload_imagefile(self, imagef: str) -> Dict:
        imageobj = create_image_file(imagef)
        result = shopify.GraphQL().execute(UPLOAD_IMAGE_QUERY, variables={"input": imageobj})
        os.remove(f"{imageobj.get('filename')}")
        result = json.loads(result)
        return result["data"]["stagedUploadTargetGenerate"]["url"]