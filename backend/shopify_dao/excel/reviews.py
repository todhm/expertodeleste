from typing import Literal, List, Dict

import pandas as pd
from pymongo.database import Database

from models.product_data import ProductData
from dataparser.image import upload_url_to_s3


def product_data_to_review_format(
    product_data: ProductData,
    state: Literal["published", "active"] = "published"
) -> List[Dict]:
    review_dict_data_list = []
    for review_data in product_data.reviewList:
        review_image_list = [upload_url_to_s3(x) for x in review_data.reviewImageList]
        pic_text = ','.join(review_image_list)
        item = {
            "title": review_data.reviewTitle,
            "body": review_data.reviewText,
            "rating": review_data.reviewPoint,
            "review_date": review_data.reviewTime,
            "reviewer_name": review_data.writer,
            "reviewer_email": f"{review_data.writer.lower()}@gmail.com",
            "product_id": product_data.shopifyId.split('/')[-1],
            "product_handle": product_data.productId,
            "reply": "",
            "picture_urls": pic_text
        }
        review_dict_data_list.append(item)
    return review_dict_data_list


def judgeme_review_excel(
    db: Database,
    additional_query = {},
) -> List[Dict]:
    default_query = {
        "reviewList.0": {
        "$exists": True
        }
    }
    default_query.update(additional_query)
    total_data_list = list(db.product.find(default_query, {"_id": False}))
    total_reivew_list = []

    for total_data in total_data_list:
        product_data = ProductData(**total_data)
        review_list = product_data_to_review_format(
            product_data
        )
        total_reivew_list.extend(review_list)
    df = pd.DataFrame(total_reivew_list)
    columns = [
        "title", "body", "rating", "review_date", "reviewer_name",
        "reviewer_email", "product_id", "product_handle", "reply",
        "picture_urls"
    ]
    df = df[columns]
    df.to_csv(f"datacollections/exceldata/reviews.csv", index=False)