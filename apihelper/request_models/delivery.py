from flask_restx import fields
from api import api


delivery_rating_model = api.model('Lately  Goods Api', {
    'originCode': fields.Integer(required=True, description='origin zipcode'),
    'destCode': fields.Integer(required=True, description='destination zipcode'),
    'weight': fields.Float(required=True, description='Test weight in LBS')
})


rating_response_model = api.model('Delivery Rating Responses', {
    "serviceName": fields.String(description='Name of delivery service', default=''),
    "expectedTransitTime": fields.String(description='Expected Transit time', default=''),
    "price": fields.String(description='Expected price of delivery Service'),
})
