import traceback

from flask import request, current_app
from flask_restx import Resource
from werkzeug.exceptions import BadRequest
from flask_restx import Namespace

from request_models.delivery import delivery_rating_model, rating_response_model
from external_requests.fedex import create_access_token, create_rating_table


ns = Namespace('delivery', 'API with delivery')


@ns.route('/shipping_rate', methods=["POST"])
class ShippiingRate(Resource):


    @ns.doc(
        body=delivery_rating_model
    )
    @ns.expect(
        delivery_rating_model,
        validate=True
    )
    @ns.marshal_list_with(rating_response_model, code=200)
    def post(self):
        try:
            access_token = create_access_token()
        except Exception:
            raise BadRequest("Error while making authorizaton fedex")
        try:
            request_data = request.get_json()
            return_list = create_rating_table(
                request_data["originCode"],
                request_data["destCode"],
                request_data["weight"],
                access_token
            )
            return return_list
        except Exception:
            error_message = f"Error while call lately data {traceback.format_exc()}"
            current_app.logger.error(error_message)
            raise BadRequest(error_message)
