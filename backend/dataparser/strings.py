import random
import string
import re
from typing import Tuple, List


def random_string(size: int = 10, chars=string.ascii_uppercase + string.digits) -> str:
    return ''.join(random.choice(chars) for _ in range(size))


def parse_specification_string(data: str) -> Tuple[float, float, float, float]:
    length_exists = re.search(r'(\d+)(\s|")*L ', data,  flags=re.IGNORECASE)
    width_exists = re.search(r'(\d+)(\s|")*W ', data,  flags=re.IGNORECASE)
    height_exits = re.search(r'(\d+)(\s|")*H ', data,  flags=re.IGNORECASE)
    weight_exists = re.search(r'(\d+)(\s|")*lbs', data,  flags=re.IGNORECASE)
    if width_exists and height_exits and length_exists and weight_exists:
        return (
            float(width_exists.group(1)), 
            float(height_exits.group(1)), 
            float(length_exists.group(1)), 
            float(weight_exists.group(1)), 
        )
    dataregex = re.search(r'(\d+)(\s|")*x(\s)*(\d+)(\s|")*x(\s)*(\d+)(\s|")*x(\s)*(\d+)(\s|")*lbs', data,  flags=re.IGNORECASE)
    if dataregex:
        length = float(dataregex.group(1))
        width = float(dataregex.group(4))
        height = float(dataregex.group(7))
        weight = float(dataregex.group(10))
        return (
            width,
            height,
            length,
            weight
        )
    # w-51.97 x d-23.62 x h-14.17 
    dataregex = re.search(r'w-(\d*\.*\d+).*d-(\d*\.*\d+).*h-(\d*\.*\d+)', data,  flags=re.IGNORECASE)
    if dataregex:
        width = float(dataregex.group(1))
        depth = float(dataregex.group(2))
        height = float(dataregex.group(3))
        return (
            width,
            height,
            depth,
            None
        )


def split_by_string_length(iterable: List[str], limit_size: int = 1500, split_with_newline: bool = True) -> List[List[str]]:
    batches = []
    inner_batches = []
    total_data_string_length = 0
    current_iteration = 0
    total_list_length = len(iterable)
    while current_iteration + 1 <= total_list_length:
        current_string = iterable[current_iteration]
        current_string_length = len(current_string)
        if split_with_newline:
            current_string_length += 1
        if current_string_length + total_data_string_length > limit_size:
            total_data_string_length = 0
            batches.append(inner_batches)
            inner_batches = []
        inner_batches.append(current_string)
        total_data_string_length += current_string_length
        current_iteration += 1
    if inner_batches:
        batches.append(inner_batches)
    return batches