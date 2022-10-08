

def test_image_upload(test_app):
    response = test_app.post(
        '/upload', 
        data={"upload": open('test.png', 'rb')},
        content_type='multipart/form-data',
    )
    result = response.json
    assert result['url'].endswith('.jpg')

