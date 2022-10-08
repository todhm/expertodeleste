import traceback
from flask import (
    request,
    Blueprint,
    current_app
)
from flask_ckeditor import upload_fail, upload_success

from s3_dao.s3_dao import S3_Dao


admin_blueprint = Blueprint('api_app', __name__)


@admin_blueprint.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('upload')
    try:
        s3_dao = S3_Dao()
        url = s3_dao.upload_data_from_file(
            f,
            folder_prefix='/description',
            quality=100,
        )
    except Exception as e:
        current_app.logger.error(traceback.format_exc())
        return upload_fail(str(e))
    return upload_success(url=url)
