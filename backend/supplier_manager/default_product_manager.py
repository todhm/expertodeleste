from typing import Dict, List
from abc import ABC, abstractmethod
import random

from models import product_data
from dataparser.numbers import round_up_decimals
from data_types.ship_type import ShipTypeType


class DefaultProductManager(ABC):

    simple_re = r"bar.*set"
    outdoor_re = r"outdoor"

    dining_match_re = r"((?=.*dining)(?=.*table))|((?=.*dining)(?=.*set))|((?=.*height)(?=.*table))|((?=.*patio)(?=.*set))|((?=.*bar)(?=.*set))|((?=.*counter)(?=.*height)(?=.*set))|outdoor.*set|coffee.*table|vanity.*table"
    coocktail_table_re = r"((?=.*cocktail)(?=.*table))"
    dining_chair_match_re = r"((?=.*dining)(?=.*chair))"
    dining_buffet_match_re = r"((?=.*dining)(?=.*buffet))"
    dark_color_re = r"black|coffee|walnut|vista grey|melamine top|dark brown|dark oak"
    bright_color_re = r"light oak|white|natural|teak|honey.*oil|reddish.*brown|gray"

    @abstractmethod
    def fetch_all_product_data_list(self) -> List[product_data.ProductData]:
        pass
    
    @abstractmethod
    def parse_shiptype_data(self, **x) -> ShipTypeType:
        pass

    @abstractmethod
    def create_product_data(self, **x) -> product_data.ProductData:  
        pass

    @abstractmethod
    def parse_inventory_stock(self, **x) -> int:
        pass

    @abstractmethod
    def fetch_single_row(self, skuId: str) -> Dict:
        pass

    @abstractmethod
    def parse_title(self, **x) -> str:
        pass
    
    @abstractmethod
    def parse_main_image_list(self, **x) -> List[str]:
        pass

    @abstractmethod
    def parse_warranty(self, **x) -> str:
        pass

    @abstractmethod
    def parse_delivery_data(self, **x) -> product_data.DeliveryData:
        pass

    @abstractmethod
    def parse_weight_info(self, **x) -> product_data.WeightInfo:
        pass

    @abstractmethod
    def parse_must_info_list(self, **x) -> List[product_data.MustInfo]:
        pass

    @abstractmethod
    def parse_feature_list(self, **x) -> List[str]:
        pass
            
            
    def make_product_description(self, product_model: product_data.ProductData, prop_sixty_five: bool = False) -> str:
        header_descriptioin = f'<p>{product_model.shortDescription}</p>'  
        li_list = []
        for feature_col in product_model.featureList:
            li_list.append(feature_col)

        feature_html = (
            '<ul class="description-feature-wrapper">' 
            + ''.join(map(lambda x: f'<li class="description-feature-list">{x.strip()}</li>', li_list)) 
            + "</ul>"
        )
        final_html = (
            '<div class="featured__product">'
            '<div class="featured_product-description txtArea"><div class="module">'
            f'<div class="product-details clearer">{header_descriptioin}</div>'
            '</div>'
            f'{feature_html}</div>'
            '</div>'
        )
        if product_model.videoUrlList:
            if product_model.videoUrlList[0].endswith(".mp4"):
                final_html += (
                    '<div class="product-video-wrapper">'
                    '<video autoplay="" controls="" height="315" muted="" width="560">'
                    f'<source src="{product_model.videoUrlList[0]}" type="video/mp4" />'
                    'Your browser does not support the video tag.</video>'
                    '</div>'
                )
            else:
                final_html += (
                    '<div class="product-video-wrapper">'
                    f'<iframe width="560" height="315" src="{product_model.videoUrlList[0]}" title="Video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'   
                    '</div>'
                )
        if prop_sixty_five:
            final_html += '<a class="warning-noti" href="https://smoothdiningbucket.s3.us-west-1.amazonaws.com/pr900.pdf" target="_blank">California Prop 65 Warning</a>'
        return final_html

    def make_before_price(self, product_model: product_data.ProductData) -> None:
        before_sales_multiple  = random.choice([1.1, 1.2, 2, 1.4, 1.5, 1.6, 1.30, 1.22])
        product_model.beforeSalePrice = round_up_decimals(before_sales_multiple * product_model.price, decimals=0)
