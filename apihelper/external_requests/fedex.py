from typing import List, Dict
import requests
from flask import current_app


def create_access_token()->str:
    data = {
        "grant_type": "client_credentials",
        "client_id": current_app.config["FEDEX_CLIENT_ID"], 
        "client_secret": current_app.config["FEDEX_CLIENT_SECRET"]
    }
    url = f'{current_app.config["FEDEX_URL"]}/oauth/token'
    response = requests.post(url, data=data).json()
    return response["access_token"]


def create_rating_table(source_zip_code: int, dest_zip_code: int, weight: float, access_token:str)->List[Dict]:
    ltl_account = current_app.config["FEDEX_LTL_ACCOUNT"]
    url = f'{current_app.config["FEDEX_URL"]}/rate/v1/rates/quotes'
    account = ltl_account
    payload = {
    "accountNumber": {
        "value": account
    },
    "rateRequestControlParameters": {
        "returnTransitTimes": True,
        "servicesNeededOnRateFailure": False,
        "variableOptions": "FREIGHT_GUARANTEE",
        "rateSortOrder": "SERVICENAMETRADITIONAL"
    },
    "requestedShipment": {
        "shipper": {
        "address": {
            "postalCode": source_zip_code,
            "countryCode": "US",
            "residential": False
        }
        },
        "recipient": {
        "address": {
            "postalCode": dest_zip_code,
            "countryCode": "US",
            "residential": True
        }
        },
        "preferredCurrency": "USD",
        "rateRequestType": [
        "ACCOUNT",
        "LIST"
        ],
        "pickupType": "USE_SCHEDULED_PICKUP",
        "requestedPackageLineItems": [
        {
            "groupPackageCount": 1,
            "weight": {
            "units": "LB",
            "value": weight
            },      
        }
        ],
        "documentShipment": True,
        "packagingType": "YOUR_PACKAGING",
    },
    "carrierCodes": [
        "FDXE",
        "FDXG",
    ]
    }
    headers = {
        'Content-Type': "application/json",
        'X-locale': "en_US",
        'Authorization': f"Bearer {access_token}"
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    result = response.json()
    result_list = []
    for data in result['output']['rateReplyDetails']:
        result_list.append(
            {
                "expectedTransitTime": data['commit']['dateDetail']['dayFormat'],
                "serviceName": data['serviceName'],
                "price": data['ratedShipmentDetails'][0]['totalNetFedExCharge'],
            }
        )
    return result_list