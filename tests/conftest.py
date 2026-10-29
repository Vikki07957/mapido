import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app(tmp_path):
    database = tmp_path / "mapido-test.sqlite"
    test_app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-session-key",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.as_posix()}",
        "WTF_CSRF_ENABLED": False,
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()