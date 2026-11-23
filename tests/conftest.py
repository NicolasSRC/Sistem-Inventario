import pytest

from app import create_app, db
from app.cli import sembrar_base


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret",
    })
    with app.app_context():
        db.create_all()
        sembrar_base()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, username, password):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


@pytest.fixture
def admin_client(app):
    client = app.test_client()
    _login(client, "admin", "admin123")
    return client


@pytest.fixture
def cajero_client(app):
    client = app.test_client()
    _login(client, "cliente", "cliente123")
    return client
