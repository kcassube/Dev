from app.extensions import db
from app.models import (
    STATUS_APPROVED,
    STATUS_PENDING,
    Redemption,
    Reward,
    Task,
    TaskCompletion,
    User,
    book_points,
)


def child(app):
    return User.query.filter_by(username="lina").first()


def task_named(title):
    return Task.query.filter_by(title=title).first()


# ------------------------------------------------------------------ Login


def test_login_required(client):
    assert client.get("/", follow_redirects=False).status_code == 302


def test_wrong_password(client):
    res = client.post("/login", data={"username": "mama", "password": "falsch"}, follow_redirects=True)
    assert "falsch" in res.get_data(as_text=True)


def test_parent_lands_in_admin(parent_client):
    assert "Übersicht" in parent_client.get("/admin/", follow_redirects=True).get_data(as_text=True)


def test_child_has_no_admin_access(child_client):
    assert child_client.get("/admin/").status_code == 403


def test_disabled_account_cannot_login(app, client):
    with app.app_context():
        user = User.query.filter_by(username="lina").first()
        user.enabled = False
        db.session.commit()
    res = client.post("/login", data={"username": "lina", "password": "1234"}, follow_redirects=True)
    assert "gesperrt" in res.get_data(as_text=True)


# --------------------------------------------------------------- Aufgaben


def test_task_needs_approval_before_points(app, child_client):
    with app.app_context():
        task_id = task_named("Zimmer aufräumen").id
    child_client.post(f"/aufgabe/{task_id}/erledigt", follow_redirects=True)
    with app.app_context():
        completion = TaskCompletion.query.one()
        assert completion.status == STATUS_PENDING
        assert child(app).balance == 0


def test_auto_approved_task_credits_immediately(app, child_client):
    with app.app_context():
        task_id = task_named("Zähne putzen").id
    child_client.post(f"/aufgabe/{task_id}/erledigt", follow_redirects=True)
    with app.app_context():
        assert child(app).balance == 2
        assert TaskCompletion.query.one().status == STATUS_APPROVED


def test_daily_task_only_once_per_day(app, child_client):
    with app.app_context():
        task_id = task_named("Zähne putzen").id
    child_client.post(f"/aufgabe/{task_id}/erledigt", follow_redirects=True)
    child_client.post(f"/aufgabe/{task_id}/erledigt", follow_redirects=True)
    with app.app_context():
        assert TaskCompletion.query.count() == 1
        assert child(app).balance == 2


def test_parent_approves_completion(app, child_client, client):
    with app.app_context():
        task_id = task_named("Zimmer aufräumen").id
    child_client.post(f"/aufgabe/{task_id}/erledigt", follow_redirects=True)
    child_client.get("/logout")
    client.post("/login", data={"username": "mama", "password": "geheim123"}, follow_redirects=True)
    with app.app_context():
        completion_id = TaskCompletion.query.one().id
    client.post(f"/admin/freigaben/aufgabe/{completion_id}/ok", follow_redirects=True)
    with app.app_context():
        assert TaskCompletion.query.one().status == STATUS_APPROVED
        assert child(app).balance == 5


def test_rejected_completion_gives_no_points(app, child_client, client):
    with app.app_context():
        task_id = task_named("Zimmer aufräumen").id
    child_client.post(f"/aufgabe/{task_id}/erledigt", follow_redirects=True)
    child_client.get("/logout")
    client.post("/login", data={"username": "mama", "password": "geheim123"}, follow_redirects=True)
    with app.app_context():
        completion_id = TaskCompletion.query.one().id
    client.post(f"/admin/freigaben/aufgabe/{completion_id}/nein", follow_redirects=True)
    with app.app_context():
        assert child(app).balance == 0


# ------------------------------------------------------------------- Shop


def test_redeem_without_points_is_blocked(app, child_client):
    with app.app_context():
        reward_id = Reward.query.first().id
    res = child_client.post(f"/shop/{reward_id}/einloesen", follow_redirects=True)
    assert "reichen deine Punkte" in res.get_data(as_text=True)
    with app.app_context():
        assert Redemption.query.count() == 0


def test_redeem_reserves_points(app, child_client):
    with app.app_context():
        kid = child(app)
        book_points(kid, 20, "Startguthaben")
        db.session.commit()
        reward_id = Reward.query.first().id
    child_client.post(f"/shop/{reward_id}/einloesen", follow_redirects=True)
    with app.app_context():
        assert child(app).balance == 10
        assert Redemption.query.one().status == STATUS_PENDING


def test_rejected_redemption_refunds(app, child_client, client):
    with app.app_context():
        book_points(child(app), 20, "Startguthaben")
        db.session.commit()
        reward_id = Reward.query.first().id
    child_client.post(f"/shop/{reward_id}/einloesen", follow_redirects=True)
    child_client.get("/logout")
    client.post("/login", data={"username": "mama", "password": "geheim123"}, follow_redirects=True)
    with app.app_context():
        redemption_id = Redemption.query.one().id
    client.post(f"/admin/freigaben/belohnung/{redemption_id}/nein", follow_redirects=True)
    with app.app_context():
        assert child(app).balance == 20


def test_stock_decreases_and_blocks(app, child_client):
    with app.app_context():
        book_points(child(app), 100, "Startguthaben")
        reward = Reward(title="Kino", cost=10, stock=1)
        db.session.add(reward)
        db.session.commit()
        reward_id = reward.id
    child_client.post(f"/shop/{reward_id}/einloesen", follow_redirects=True)
    res = child_client.post(f"/shop/{reward_id}/einloesen", follow_redirects=True)
    assert "nicht verfügbar" in res.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Reward, reward_id).stock == 0


# ---------------------------------------------------------- Adminfunktionen


def test_admin_creates_task(app, parent_client):
    parent_client.post(
        "/admin/aufgaben/neu",
        data={
            "title": "Staubsaugen",
            "description": "",
            "icon": "🧹",
            "points": "4",
            "recurrence": "weekly",
            "requires_approval": "y",
            "active": "y",
        },
        follow_redirects=True,
    )
    with app.app_context():
        assert task_named("Staubsaugen").points == 4


def test_admin_creates_reward(app, parent_client):
    parent_client.post(
        "/admin/belohnungen/neu",
        data={"title": "Zoo", "description": "", "icon": "🦁", "cost": "50", "stock": "", "active": "y"},
        follow_redirects=True,
    )
    with app.app_context():
        reward = Reward.query.filter_by(title="Zoo").first()
        assert reward.cost == 50 and reward.stock is None


def test_admin_creates_child_account(app, parent_client):
    parent_client.post(
        "/admin/konten/neu",
        data={
            "username": "Tom",
            "display_name": "Tom",
            "avatar": "🐸",
            "role": "child",
            "password": "4321",
            "confirm": "4321",
            "enabled": "y",
        },
        follow_redirects=True,
    )
    with app.app_context():
        user = User.query.filter_by(username="tom").first()
        assert user is not None and user.check_password("4321")


def test_duplicate_username_rejected(app, parent_client):
    res = parent_client.post(
        "/admin/konten/neu",
        data={
            "username": "lina",
            "display_name": "Lina 2",
            "avatar": "🐸",
            "role": "child",
            "password": "4321",
            "confirm": "4321",
            "enabled": "y",
        },
        follow_redirects=True,
    )
    assert "schon" in res.get_data(as_text=True)


def test_manual_point_adjustment(app, parent_client):
    with app.app_context():
        kid_id = child(app).id
    parent_client.post(
        "/admin/punkte",
        data={"child_id": str(kid_id), "delta": "-3", "reason": "Streit"},
        follow_redirects=True,
    )
    with app.app_context():
        assert child(app).balance == -3


def test_last_parent_cannot_be_deleted(app, parent_client):
    with app.app_context():
        parent_id = User.query.filter_by(username="mama").first().id
    parent_client.post(f"/admin/konten/{parent_id}/loeschen", follow_redirects=True)
    with app.app_context():
        assert User.query.filter_by(username="mama").first() is not None


def test_task_assigned_to_other_child_is_hidden(app, parent_client, client):
    with app.app_context():
        other = User(username="tom", display_name="Tom", role="child")
        other.set_password("4321")
        db.session.add(other)
        db.session.commit()
        task = task_named("Zimmer aufräumen")
        task.assignees = [other]
        db.session.commit()
    client.post("/login", data={"username": "lina", "password": "1234"}, follow_redirects=True)
    res = client.get("/")
    assert "Zimmer aufräumen" not in res.get_data(as_text=True)
