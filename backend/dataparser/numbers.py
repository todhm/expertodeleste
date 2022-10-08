from math import ceil, floor
from typing import Union


def round_up_decimals(price, decimals=-1):
    multiplier = 10 ** decimals
    round_up_price = ceil(price * multiplier) / multiplier
    return round_up_price


def round_down_decimals(price: Union[float, int], decimals: int = -1):
    multiplier = 10 ** decimals
    round_up_price = floor(price * multiplier) / multiplier
    return round_up_price
