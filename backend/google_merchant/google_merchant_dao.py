from typing import List
import pandas as pd

from models.product_data import ProductData
from google_merchant.gooogle_merchant_parser import GoogleMerchantParser

class GoogleMerchantDao(object):

    def to_df(self, data_list: List[ProductData]) -> pd.DataFrame:
        return_list = []
        for data in data_list:
            return_list.extend(GoogleMerchantParser.parse_product_data(data))
        df = pd.DataFrame(return_list)
        return df

    def to_local_excel(self, data_list: List[ProductData], fname: str = "googlemerchant.csv") -> pd.DataFrame:
        df = self.to_df(data_list)
        df.to_csv(f"datacollections/{fname}", index=False)
        return df
        
        


    