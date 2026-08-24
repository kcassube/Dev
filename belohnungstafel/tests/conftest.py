import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.config import TestConfig  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import ROLE_CHILD, ROLE_PARENT, Reward, Task, User  # noqa: E402


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        parent = User(username="mama", display_name="Mama", role=ROLE_PARENT)
        parent.set_password("geheim123")
        kid = User(username="lina", display_name="Lina", role=ROLE_CHILD, avatar="🦊")
        kid.set_password("1234")
        db.session.add_all([parent, kid])
        db.session.add(Task(title="Zimmer aufräumen", points=5, recurrence="daily"))
        db.session.add(
            Task(title="Zähne putzen", points=2, recurrence="daily", requires_approval=False)
        )
        db.session.add(Reward(title="Eis", cost=10))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, username, password):
    return client.post(
        "/login", data={"username": username, "password": password}, follow_redirects=True
    )


@pytest.fixture
def parent_client(client):
    _login(client, "mama", "geheim123")
    return client


@pytest.fixture
def child_client(client):
    _login(client, "lina", "1234")
    return client
