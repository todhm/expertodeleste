import logging
import asyncio

from pymongo import MongoClient
from flask.cli import AppGroup

from models.product_data import BrandData
from mongodao.mongo_dao import MongoDao
from supplier_manager.andersonteak.product_manager import AndersonTeakProductManager
from supplier_manager.acme.product_manager import AcmeProductManager
from supplier_manager.winsome.product_manager import WinsomeProductManager
from supplier_manager.vifah.product_manager import VifahProductManager
from supplier_manager.manhattan.product_manager import ManhattanProductManager
from supplier_manager.art.product_manager import ArtProductManager
from data_types import brand_types
from shopify_dao.product import ProductDao
from shopify_dao.shop_app import create_shopify_app
from config import ProductionConfig
from dataparser.htmlparser import make_inline_style


logger = logging.getLogger(__name__)


supplier_cli = AppGroup('supplier')

default_anderson_path: str = 'datacollections/andersonteak/andersonproductsnew.xlsx'
default_anderson_inv_path: str = 'datacollections/andersonteak/inventorynew.csv'
default_acme_path: str = 'datacollections/acme/products.csv'
defalt_acme_price_path: str = 'datacollections/acme/price.csv'
default_acme_image_path: str = 'datacollections/acme/images.csv'
default_winsome_path: str = 'datacollections/winsome/products.xlsx'
default_winsome_stock_path: str = 'datacollections/winsome/stocks.xlsx'
default_manhattan_path: str = 'datacollections/manhattan/data.xlsx'
default_manhattan_stock_path: str = 'datacollections/manhattan/inventory.xlsx'
default_vifah_home: str = 'datacollections/vifah/home.xlsx'
default_vifah_office: str = 'datacollections/vifah/office.xlsx'
default_vifah_outdoor = 'datacollections/vifah/outdoor.xlsx'
default_vifah_inventory = 'datacollections/vifah/inventory.csv'
default_art_path: str = 'datacollections/art/data.xlsx'
default_art_stock_path: str = 'datacollections/art/inventory.xlsx'

@supplier_cli.command('andersonteak')
def crawl_links():
    fname = input('check your product fname')
    if not fname:
        fname = default_anderson_path
    inventory = input('check your inventory fname')
    if not inventory:
        inventory = default_anderson_inv_path
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        product_dao = ProductDao(shop, db)
        brand_data = db.brand_data.find_one({"brandName": brand_types.ANDERSON_TEAK}, {"_id": False})
        brand_data = BrandData(**brand_data)
        brand_data.brandDescription = make_inline_style(brand_data.brandDescription)
        atm = AndersonTeakProductManager(
            product_dao,
            brand_data,
            default_product_path=fname,
            inventory_product_path=inventory
        )
        atm.upsert_all_anderson_data()


@supplier_cli.command('acme')
def acme_func():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    fname = input('check your product fname')
    if not fname:
        fname = default_acme_path
    price = input('check your inventory fname')
    if not price:
        price = defalt_acme_price_path
    images = input('check your inventory fname')
    if not images:
        images = default_acme_image_path
    index = input('check your start index')
    if not index:
        index = 0
    else:
        index = int(index)
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        product_dao = ProductDao(shop, db)
        brand_data = db.brand_data.find_one({"brandName": brand_types.ACME_FURNITURE}, {"_id": False})
        brand_data = BrandData(**brand_data)
        brand_data.brandDescription = make_inline_style(brand_data.brandDescription)
        atm = AcmeProductManager(
            product_dao,
            brand_data,
            product_path=fname,
            image_path=images,
            price_path=price,
            start_index=index
        )
        loop.run_until_complete(atm.upsert_all_acme_data())
    loop.close()


@supplier_cli.command('winsome')
def winsome_func():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    fname = input('check your product path')
    if not fname:
        fname = default_winsome_path
    stock_path = input('check your inventory fname')
    if not stock_path:
        stock_path = default_winsome_stock_path
    index = input('check your start index')
    if not index:
        index = 0
    else:
        index = int(index)
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        product_dao = ProductDao(shop, db)
        brand_data = db.brand_data.find_one({"brandName": brand_types.WINSOME}, {"_id": False})
        brand_data = BrandData(**brand_data)
        brand_data.brandDescription = make_inline_style(brand_data.brandDescription)
        atm = WinsomeProductManager(
            product_dao,
            brand_data,
            product_path=fname,
            stock_path=stock_path,
            start_index=index
        )
        loop.run_until_complete(atm.upsert_all_product_data())
    loop.close()


@supplier_cli.command('vifah')
def vifah_func():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    homefname = input('check your home product path')
    if not homefname:
        homefname = default_vifah_home
    officefname = input('check your office product path')
    if not officefname:
        officefname = default_vifah_office
    outdoorfname = input('check your office product path')
    if not outdoorfname:
        outdoorfname = default_vifah_outdoor
    inventory_fname = input('check your inventory fname')
    if not inventory_fname:
        inventory_fname = default_vifah_inventory
    index = input('check your start index')
    if not index:
        index = 0
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        product_dao = ProductDao(shop, db)
        brand_data = db.brand_data.find_one({"brandName": brand_types.VIFAH}, {"_id": False})
        brand_data = BrandData(**brand_data)
        brand_data.brandDescription = make_inline_style(brand_data.brandDescription)
        atm = VifahProductManager(
            product_dao,
            brand_data,
            home_path=homefname,
            office_path=officefname,
            outdoor_path=outdoorfname,
            inventory_product_path=inventory_fname,
            start_index=index
        )
        loop.run_until_complete(atm.upsert_all_product_data())
    loop.close()


@supplier_cli.command('manhattan')
def manhattan_func():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    homefname = input('check your home product path')
    if not homefname:
        homefname = default_manhattan_path
    inventory_fname = input('check your inventory path')
    if not inventory_fname:
        inventory_fname = default_manhattan_stock_path
    index = input('check your start index')
    if not index:
        index = 0
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        product_dao = ProductDao(shop, db)
        brand_data = db.brand_data.find_one({"brandName": brand_types.MANHATTAAN_COMFORT}, {"_id": False})
        brand_data = BrandData(**brand_data)
        brand_data.brandDescription = make_inline_style(brand_data.brandDescription)
        atm = ManhattanProductManager(
            product_dao,
            brand_data,
            product_path=homefname,
            stock_path=inventory_fname,
            start_index=index
        )
        loop.run_until_complete(atm.upsert_all_product_data())
    loop.close()


@supplier_cli.command('shiptype')
def produttype_fix():
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        product_dao = ProductDao(shop, db)
        mongo_dao = MongoDao(db)
        brand_data = db.brand_data.find_one({"brandName": brand_types.MANHATTAAN_COMFORT}, {"_id": False})
        brand_data = BrandData(**brand_data)
        brand_data.brandDescription = make_inline_style(brand_data.brandDescription)
        data_list = [(
            brand_types.MANHATTAAN_COMFORT, ManhattanProductManager(
                product_dao,
                brand_data,
                product_path=default_manhattan_path,
                stock_path=default_manhattan_stock_path,
                start_index=0
            )
        ),
        (
            brand_types.VIFAH, VifahProductManager(
                product_dao,
                brand_data,
                default_vifah_home,
                default_vifah_outdoor,
                default_vifah_office,
                default_vifah_inventory,
                start_index=0
            )
        ),
        (
            brand_types.ACME_FURNITURE, AcmeProductManager(
                product_dao,
                brand_data,
                default_acme_path,
                default_acme_image_path,
                defalt_acme_price_path,
                start_index=0
            )
        ),
        (
            brand_types.ANDERSON_TEAK, AndersonTeakProductManager(
                product_dao,
                brand_data,
                default_anderson_path,
                default_anderson_inv_path,
            )
        ),
        (
            brand_types.WINSOME, WinsomeProductManager(
                product_dao,
                brand_data,
                default_winsome_path,
                default_winsome_stock_path
            )
        )
        ]
        for brand_name, bpm in data_list:
            product_data_list = mongo_dao.fetch_product_list_data({"brandName": brand_name})
            for product_data in product_data_list:
                if brand_name != brand_types.WINSOME:
                    data = bpm.fetch_single_row(product_data.productId)
                    product_data.shipType = bpm.parse_shiptype_data(data)
                    print(product_data.shipType)
                else:
                    product_data.shipType = bpm.parse_shiptype_data(product_data.weightInfoList)
                    print(product_data.shipType)
                mongo_dao.upsert_mongo_product_data(product_data, ["shipType"])
    

@supplier_cli.command('art')
def art_func():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    homefname = input('check your home product path')
    if not homefname:
        homefname = default_art_path
    inventory_fname = input('check your inventory path')
    if not inventory_fname:
        inventory_fname = default_art_stock_path
    index = input('check your start index')
    if not index:
        index = 0
    with MongoClient(ProductionConfig.MONGO_URI) as client:
        db = client[ProductionConfig.DB_NAME]
        shop = create_shopify_app()
        product_dao = ProductDao(shop, db)
        brand_data = db.brand_data.find_one({"brandName": brand_types.ART_FURNITURE}, {"_id": False})
        brand_data = BrandData(**brand_data)
        brand_data.brandDescription = make_inline_style(brand_data.brandDescription)
        atm = ArtProductManager(
            product_dao,
            brand_data,
            product_path=homefname,
            stock_path=inventory_fname,
            start_index=index
        )
        loop.run_until_complete(atm.upsert_all_product_data())
    loop.close()