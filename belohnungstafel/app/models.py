from datetime import date, datetime, time, timedelta

from flask_login import UserMixin
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

ROLE_PARENT = "parent"
ROLE_CHILD = "child"

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

RECURRENCE_LABELS = {
    "daily": "täglich",
    "weekly": "wöchentlich",
    "once": "einmalig",
}


def local_now():
    """Ortszeit ohne Zeitzoneninfo.

    Die Tafel läuft in einem Haushalt, also in einer Zeitzone. Ortszeit sorgt
    dafür, dass angezeigte Zeiten stimmen und ein neuer Tag um Mitternacht
    beginnt – dieselbe Grenze, die auch ``period_start`` benutzt.
    """
    return datetime.now()


def period_start(recurrence, today=None):
    """Beginn des aktuellen Zeitfensters einer Aufgabe (None = unbegrenzt)."""
    today = today or date.today()
    if recurrence == "daily":
        return datetime.combine(today, time.min)
    if recurrence == "weekly":
        return datetime.combine(today - timedelta(days=today.weekday()), time.min)
    return None


task_assignments = db.Table(
    "task_assignments",
    db.Column("task_id", db.Integer, db.ForeignKey("task.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(64), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), nullable=False, default=ROLE_CHILD)
    avatar = db.Column(db.String(8), nullable=False, default="🙂")
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=local_now)

    transactions = db.relationship(
        "PointTransaction",
        foreign_keys="PointTransaction.child_id",
        back_populates="child",
        cascade="all, delete-orphan",
    )
    completions = db.relationship(
        "TaskCompletion",
        foreign_keys="TaskCompletion.child_id",
        back_populates="child",
        cascade="all, delete-orphan",
    )
    redemptions = db.relationship(
        "Redemption",
        foreign_keys="Redemption.child_id",
        back_populates="child",
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):  # von Flask-Login ausgewertet
        return self.enabled

    @property
    def is_parent(self):
        return self.role == ROLE_PARENT

    @property
    def balance(self):
        total = (
            db.session.query(func.coalesce(func.sum(PointTransaction.delta), 0))
            .filter(PointTransaction.child_id == self.id)
            .scalar()
        )
        return int(total or 0)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    points = db.Column(db.Integer, nullable=False, default=1)
    icon = db.Column(db.String(8), nullable=False, default="⭐")
    recurrence = db.Column(db.String(16), nullable=False, default="daily")
    requires_approval = db.Column(db.Boolean, nullable=False, default=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=local_now)

    assignees = db.relationship("User", secondary=task_assignments, backref="tasks")
    completions = db.relationship(
        "TaskCompletion", back_populates="task", cascade="all, delete-orphan"
    )

    @property
    def recurrence_label(self):
        return RECURRENCE_LABELS.get(self.recurrence, self.recurrence)

    def is_for(self, child):
        """Ohne Zuweisung gilt die Aufgabe für alle Kinder."""
        return not self.assignees or child in self.assignees

    def open_for(self, child):
        """True, wenn das Kind die Aufgabe im aktuellen Zeitfenster noch erledigen darf."""
        query = TaskCompletion.query.filter(
            TaskCompletion.task_id == self.id,
            TaskCompletion.child_id == child.id,
            TaskCompletion.status.in_([STATUS_PENDING, STATUS_APPROVED]),
        )
        start = period_start(self.recurrence)
        if start is not None:
            query = query.filter(TaskCompletion.submitted_at >= start)
        return query.first() is None

    def __repr__(self):
        return f"<Task {self.title}>"


class Reward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    cost = db.Column(db.Integer, nullable=False, default=10)
    icon = db.Column(db.String(8), nullable=False, default="🎁")
    stock = db.Column(db.Integer, nullable=True)  # None = unbegrenzt
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=local_now)

    redemptions = db.relationship(
        "Redemption", back_populates="reward", cascade="all, delete-orphan"
    )

    @property
    def in_stock(self):
        return self.stock is None or self.stock > 0

    def __repr__(self):
        return f"<Reward {self.title}>"


class TaskCompletion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(16), nullable=False, default=STATUS_PENDING)
    points = db.Column(db.Integer, nullable=False, default=0)
    note = db.Column(db.String(255), default="")
    submitted_at = db.Column(db.DateTime, nullable=False, default=local_now)
    decided_at = db.Column(db.DateTime)
    decided_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    task = db.relationship("Task", back_populates="completions")
    child = db.relationship("User", foreign_keys=[child_id], back_populates="completions")
    decided_by = db.relationship("User", foreign_keys=[decided_by_id])


class Redemption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reward_id = db.Column(db.Integer, db.ForeignKey("reward.id"), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(16), nullable=False, default=STATUS_PENDING)
    cost = db.Column(db.Integer, nullable=False, default=0)
    note = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, nullable=False, default=local_now)
    decided_at = db.Column(db.DateTime)
    decided_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    reward = db.relationship("Reward", back_populates="redemptions")
    child = db.relationship("User", foreign_keys=[child_id], back_populates="redemptions")
    decided_by = db.relationship("User", foreign_keys=[decided_by_id])


class PointTransaction(db.Model):
    """Kontobewegung – der Punktestand ist immer die Summe dieser Zeilen."""

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    delta = db.Column(db.Integer, nullable=False)
    kind = db.Column(db.String(16), nullable=False, default="manual")
    reason = db.Column(db.String(255), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=local_now)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    child = db.relationship("User", foreign_keys=[child_id], back_populates="transactions")
    created_by = db.relationship("User", foreign_keys=[created_by_id])


def book_points(child, delta, reason, kind="manual", actor=None):
    entry = PointTransaction(
        child_id=child.id,
        delta=int(delta),
        reason=reason,
        kind=kind,
        created_by_id=actor.id if actor else None,
    )
    db.session.add(entry)
    return entry


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
