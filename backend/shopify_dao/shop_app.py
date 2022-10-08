import shopify
from shopify.resources.shop import Shop
from config import BaseConfig



def create_shopify_app() -> Shop:
    shopify.ShopifyResource.set_site(BaseConfig.SHOP_FULL_URL)
    shop = shopify.Shop.current()
    session = shopify.Session(BaseConfig.BASE_SHOP_URL, BaseConfig.API_VERSION, BaseConfig.SHOP_PASS)
    shopify.ShopifyResource.activate_session(session)
    return shop


