import json

from shopify_dao.inventory import InventoryDao



def test_inventory(shop, mongodb):
    inventory_dao = InventoryDao(shop, mongodb)
    result = inventory_dao.fetch_inventory_map()
    assert type(result) is dict
    assert len(result.keys()) > 0


def test_inventory_id(shop, mongodb):
    inventory_dao = InventoryDao(shop, mongodb)
    result = inventory_dao.fetch_default_inventory_id()
    assert type(result) is str
    assert len(result) > 0