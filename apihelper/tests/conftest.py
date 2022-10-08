import pytest

from application import create_app


@pytest.fixture(scope="session")
def test_app():
    # set up
    app = create_app()
    with app.app_context():
        client = app.test_client()
        yield client
