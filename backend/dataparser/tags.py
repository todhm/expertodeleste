from typing import Optional
import re

from models.product_data import ProductData, MustInfo
from .product import calculate_review_average, calculate_sales_percentage
from data_types import tag_types

def calculate_area_from_info(info_data: MustInfo) -> Optional[float]:
    width = None
    length = None
    target_key = '(table dimensions|^dimensions)'
    length_regex = r"(\d+\.*\d*)\s*(L|D|diam|H)"
    secondary_length_regex = r"(L|D|diam|H)-(\d+\.*\d*)"
    width_regex = r"(\d+\.*\d*)\s*W"
    secondary_width_regex = r"W-(\d+\.*\d*)"
    diameter_regex = r"(\d+\.*\d*)\s*(D|diam)"
    chair_regex = r"(bench|chair|corner|overall|cabinet|stool)"
    if re.search(target_key, info_data.key.lower()):
        for value in info_data.valueList:
            if re.search(chair_regex, value, flags=re.IGNORECASE):
                continue
            if re.search(length_regex, value, flags=re.IGNORECASE):
                length = float(re.search(length_regex, value).group(1))
            if re.search(secondary_length_regex, value, flags=re.IGNORECASE):
                length = float(re.search(secondary_length_regex, value).group(2))
            if re.search(width_regex, value, flags=re.IGNORECASE):
                width = float(re.search(width_regex, value).group(1))
            if re.search(secondary_width_regex, value, flags=re.IGNORECASE):
                width = float(re.search(secondary_width_regex, value).group(1))
            if width and length:
                return width * length
            if length and not width and re.search(diameter_regex, value):
                return (length / 2) ** 2 * 3.14

            
def fetch_seat_counts(info_data: MustInfo, product_data: ProductData) -> Optional[float]:
    target_key = 'seating'
    person_regex = r"(\d+)\s*person"
    pcs_regex = r"(\d+)\s*(pc|pieces)"

    total_seat_counts = 0
    if re.search(target_key, info_data.key, flags=re.IGNORECASE):
        for value in info_data.valueList:
            if re.search(person_regex, value, flags=re.IGNORECASE):
                total_seat_counts += int(re.search(person_regex, value, flags=re.IGNORECASE).group(1))
    if not total_seat_counts and re.search(pcs_regex, product_data.goodsName, flags=re.IGNORECASE):
        count = int(re.search(pcs_regex, product_data.goodsName, flags=re.IGNORECASE).group(1))
        total_seat_counts = count - 1
    return total_seat_counts


def add_additional_tag_to_product(product_data: ProductData):
    area = None
    person_count = None
    review_average = calculate_review_average(product_data)
    if review_average > 4.5:
        product_data.add_tag("Top Rated")
    if len(product_data.reviewList) > 10:
        product_data.add_tag("Best Sellers")
    sales_percentage = calculate_sales_percentage(product_data)
    if sales_percentage > 30:
        product_data.add_tag("Big Sales")
    if product_data.weightInfo and product_data.weightInfo.width and product_data.weightInfo.length:
        area = product_data.weightInfo.width * product_data.weightInfo.length
    for info_data in product_data.goodsMustInfo:
        if not area:
            area = calculate_area_from_info(info_data)
        if not person_count:
            person_count = fetch_seat_counts(info_data, product_data)
    if person_count:
        product_data.add_tag(f"{person_count} Seats")

    if area:
        if area >= 2000:
            product_data.add_tag("Big")
        elif area <= 1000:
            product_data.add_tag("Small")
        else:
            product_data.add_tag("Medium")
    if product_data.shipType == tag_types.LTL:
        product_data.add_tag(tag_types.LTL)
    elif product_data.shipType == tag_types.PARCEL:
        product_data.add_tag(tag_types.PARCEL)
    remove_none_table_tags(product_data)

def remove_none_table_tags(product_data: ProductData) -> None:
    tag_set_list = set(product_data.tagList)
    if tag_types.NONE_TABLE in tag_set_list:
        tag_set_list = tag_set_list - set([
            tag_types.OUTDOOR,
            tag_types.SIMPLE,
            tag_types.CLASSICS,
            tag_types.MODERN,
            tag_types.SMALL,
            tag_types.MEDIUM,
            tag_types.BIG,
            tag_types.BRIGHT,
            tag_types.DARK
        ])
        product_data.tagList = list(tag_set_list)


def change_tag_name_list(tag_name: str) -> str:
    if tag_name == "Size:Big":
        return "Big"
    elif tag_name == "Size:Small":
        return "Small"
    elif tag_name == "Size:Medium":
        return "Medium"
    elif tag_name == "Mood:Bright":
        return "Bright"
    elif tag_name == "Mood:Dark":
        return "Dark"
    elif re.search(r"SeatCount:(\d+)", tag_name):
        num_seats = re.search(r"SeatCount:(\d+)", tag_name).group(1)
        return f"{num_seats} Seats"
    else:
        return tag_name
    