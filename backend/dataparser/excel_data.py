import pandas as pd


def check_field_exists(data):
    field_exists = not pd.isnull(data) and data
    if field_exists and type(data) is str:
        field_exists = data.strip() not in ["NA", 'na', "nan", '']
    return field_exists
