from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import DecisionForm, PointAdjustForm, RewardForm, TaskForm, UserForm
from ..models import (
    ROLE_CHILD,
    ROLE_PARENT,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    PointTransaction,
    Redemption,
    Reward,
    Task,
    TaskCompletion,
    User,
    book_points,
    local_now,
)
from ..security import parent_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


def children():
    return User.query.filter_by(role=ROLE_CHILD).order_by(User.display_name).all()


def parents():
    return User.query.filter_by(role=ROLE_PARENT).order_by(User.display_name).all()


@bp.route("/")
@login_required
@parent_required
def dashboard():
    open_tasks = TaskCompletion.query.filter_by(status=STATUS_PENDING).count()
    open_rewards = Redemption.query.filter_by(status=STATUS_PENDING).count()
    kids = children()
    return render_template(
        "admin/dashboard.html",
        kids=kids,
        open_tasks=open_tasks,
        open_rewards=open_rewards,
        task_count=Task.query.filter_by(active=True).count(),
        reward_count=Reward.query.filter_by(active=True).count(),
    )


# ---------------------------------------------------------------- Freigaben


@bp.route("/freigaben")
@login_required
@parent_required
def approvals():
    completions = (
        TaskCompletion.query.filter_by(status=STATUS_PENDING)
        .order_by(TaskCompletion.submitted_at)
        .all()
    )
    redemptions = (
        Redemption.query.filter_by(status=STATUS_PENDING).order_by(Redemption.created_at).all()
    )
    return render_template(
        "admin/approvals.html",
        completions=completions,
        redemptions=redemptions,
        form=DecisionForm(),
    )


def _decide(form):
    if not form.validate_on_submit():
        flash("Ungültige Anfrage.", "error")
        return False
    return True


@bp.route("/freigaben/aufgabe/<int:completion_id>/<decision>", methods=["POST"])
@login_required
@parent_required
def decide_completion(completion_id, decision):
    form = DecisionForm()
    if not _decide(form):
        return redirect(url_for("admin.approvals"))
    if decision not in ("ok", "nein"):
        abort(404)

    completion = db.get_or_404(TaskCompletion, completion_id)
    if completion.status != STATUS_PENDING:
        flash("Diese Aufgabe wurde bereits entschieden.", "info")
        return redirect(url_for("admin.approvals"))

    completion.decided_at = local_now()
    completion.decided_by_id = current_user.id
    completion.note = form.note.data or ""
    if decision == "ok":
        completion.status = STATUS_APPROVED
        book_points(
            completion.child,
            completion.points,
            f"Aufgabe: {completion.task.title}",
            kind="task",
            actor=current_user,
        )
        flash(f"{completion.child.display_name} bekommt {completion.points} Punkte.", "success")
    else:
        completion.status = STATUS_REJECTED
        flash("Aufgabe abgelehnt.", "info")
    db.session.commit()
    return redirect(url_for("admin.approvals"))


@bp.route("/freigaben/belohnung/<int:redemption_id>/<decision>", methods=["POST"])
@login_required
@parent_required
def decide_redemption(redemption_id, decision):
    form = DecisionForm()
    if not _decide(form):
        return redirect(url_for("admin.approvals"))
    if decision not in ("ok", "nein"):
        abort(404)

    redemption = db.get_or_404(Redemption, redemption_id)
    if redemption.status != STATUS_PENDING:
        flash("Dieser Wunsch wurde bereits entschieden.", "info")
        return redirect(url_for("admin.approvals"))

    redemption.decided_at = local_now()
    redemption.decided_by_id = current_user.id
    redemption.note = form.note.data or ""
    if decision == "ok":
        redemption.status = STATUS_APPROVED
        flash(f"„{redemption.reward.title}“ freigegeben.", "success")
    else:
        redemption.status = STATUS_REJECTED
        book_points(
            redemption.child,
            redemption.cost,
            f"Erstattung: {redemption.reward.title}",
            kind="refund",
            actor=current_user,
        )
        if redemption.reward.stock is not None:
            redemption.reward.stock += 1
        flash("Wunsch abgelehnt – die Punkte wurden zurückgebucht.", "info")
    db.session.commit()
    return redirect(url_for("admin.approvals"))


# ------------------------------------------------------------------- Konten


@bp.route("/konten")
@login_required
@parent_required
def users():
    return render_template("admin/users.html", kids=children(), grownups=parents())


def _apply_user_form(form, user, is_new):
    username = form.username.data.strip().lower()
    existing = User.query.filter_by(username=username).first()
    if existing and existing.id != user.id:
        flash("Diesen Benutzernamen gibt es schon.", "error")
        return False
    if is_new and not form.password.data:
        flash("Für ein neues Konto wird ein Passwort gebraucht.", "error")
        return False

    user.username = username
    user.display_name = form.display_name.data.strip()
    user.avatar = (form.avatar.data or "🙂").strip()[:8]
    user.role = form.role.data
    user.enabled = form.enabled.data
    if form.password.data:
        user.set_password(form.password.data)
    return True


@bp.route("/konten/neu", methods=["GET", "POST"])
@login_required
@parent_required
def user_create():
    form = UserForm()
    if form.validate_on_submit():
        user = User()
        if _apply_user_form(form, user, is_new=True):
            db.session.add(user)
            db.session.commit()
            flash(f"Konto für {user.display_name} angelegt.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, user=None)


@bp.route("/konten/<int:user_id>", methods=["GET", "POST"])
@login_required
@parent_required
def user_edit(user_id):
    user = db.get_or_404(User, user_id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        if user.id == current_user.id and (form.role.data != ROLE_PARENT or not form.enabled.data):
            flash("Du kannst dir nicht selbst die Elternrechte entziehen.", "error")
        elif _apply_user_form(form, user, is_new=False):
            db.session.commit()
            flash("Konto gespeichert.", "success")
            return redirect(url_for("admin.users"))
    form.password.data = ""
    return render_template("admin/user_form.html", form=form, user=user)


@bp.route("/konten/<int:user_id>/loeschen", methods=["POST"])
@login_required
@parent_required
def user_delete(user_id):
    form = DecisionForm()
    if not _decide(form):
        return redirect(url_for("admin.users"))
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("Das eigene Konto kann nicht gelöscht werden.", "error")
    elif user.is_parent and len(parents()) <= 1:
        flash("Es muss mindestens ein Elternkonto geben.", "error")
    else:
        db.session.delete(user)
        db.session.commit()
        flash("Konto gelöscht.", "info")
    return redirect(url_for("admin.users"))


# ----------------------------------------------------------------- Aufgaben


@bp.route("/aufgaben")
@login_required
@parent_required
def tasks():
    return render_template(
        "admin/tasks.html",
        tasks=Task.query.order_by(Task.active.desc(), Task.title).all(),
        form=DecisionForm(),
    )


def _task_form(task=None):
    form = TaskForm(obj=task)
    form.assignees.choices = [(c.id, f"{c.avatar} {c.display_name}") for c in children()]
    return form


@bp.route("/aufgaben/neu", methods=["GET", "POST"])
@login_required
@parent_required
def task_create():
    form = _task_form()
    if form.validate_on_submit():
        task = Task()
        _apply_task(form, task)
        db.session.add(task)
        db.session.commit()
        flash("Aufgabe angelegt.", "success")
        return redirect(url_for("admin.tasks"))
    return render_template("admin/task_form.html", form=form, task=None)


def _apply_task(form, task):
    task.title = form.title.data.strip()
    task.description = form.description.data or ""
    task.icon = (form.icon.data or "⭐").strip()[:8]
    task.points = form.points.data
    task.recurrence = form.recurrence.data
    task.requires_approval = form.requires_approval.data
    task.active = form.active.data
    chosen = set(form.assignees.data or [])
    task.assignees = [c for c in children() if c.id in chosen]


@bp.route("/aufgaben/<int:task_id>", methods=["GET", "POST"])
@login_required
@parent_required
def task_edit(task_id):
    task = db.get_or_404(Task, task_id)
    form = _task_form(task)
    if form.validate_on_submit():
        _apply_task(form, task)
        db.session.commit()
        flash("Aufgabe gespeichert.", "success")
        return redirect(url_for("admin.tasks"))
    form.assignees.data = [c.id for c in task.assignees]
    return render_template("admin/task_form.html", form=form, task=task)


@bp.route("/aufgaben/<int:task_id>/loeschen", methods=["POST"])
@login_required
@parent_required
def task_delete(task_id):
    form = DecisionForm()
    if not _decide(form):
        return redirect(url_for("admin.tasks"))
    task = db.get_or_404(Task, task_id)
    db.session.delete(task)
    db.session.commit()
    flash("Aufgabe gelöscht.", "info")
    return redirect(url_for("admin.tasks"))


# -------------------------------------------------------------- Belohnungen


@bp.route("/belohnungen")
@login_required
@parent_required
def rewards():
    return render_template(
        "admin/rewards.html",
        rewards=Reward.query.order_by(Reward.active.desc(), Reward.cost).all(),
        form=DecisionForm(),
    )


def _apply_reward(form, reward):
    reward.title = form.title.data.strip()
    reward.description = form.description.data or ""
    reward.icon = (form.icon.data or "🎁").strip()[:8]
    reward.cost = form.cost.data
    reward.stock = form.stock.data if form.stock.data is not None else None
    reward.active = form.active.data


@bp.route("/belohnungen/neu", methods=["GET", "POST"])
@login_required
@parent_required
def reward_create():
    form = RewardForm()
    if form.validate_on_submit():
        reward = Reward()
        _apply_reward(form, reward)
        db.session.add(reward)
        db.session.commit()
        flash("Belohnung angelegt.", "success")
        return redirect(url_for("admin.rewards"))
    return render_template("admin/reward_form.html", form=form, reward=None)


@bp.route("/belohnungen/<int:reward_id>", methods=["GET", "POST"])
@login_required
@parent_required
def reward_edit(reward_id):
    reward = db.get_or_404(Reward, reward_id)
    form = RewardForm(obj=reward)
    if form.validate_on_submit():
        _apply_reward(form, reward)
        db.session.commit()
        flash("Belohnung gespeichert.", "success")
        return redirect(url_for("admin.rewards"))
    return render_template("admin/reward_form.html", form=form, reward=reward)


@bp.route("/belohnungen/<int:reward_id>/loeschen", methods=["POST"])
@login_required
@parent_required
def reward_delete(reward_id):
    form = DecisionForm()
    if not _decide(form):
        return redirect(url_for("admin.rewards"))
    reward = db.get_or_404(Reward, reward_id)
    db.session.delete(reward)
    db.session.commit()
    flash("Belohnung gelöscht.", "info")
    return redirect(url_for("admin.rewards"))


# ------------------------------------------------------------------- Punkte


@bp.route("/punkte", methods=["GET", "POST"])
@login_required
@parent_required
def points():
    form = PointAdjustForm()
    kids = children()
    form.child_id.choices = [(c.id, f"{c.avatar} {c.display_name}") for c in kids]
    if form.validate_on_submit():
        child = db.session.get(User, form.child_id.data)
        if child is None or child.is_parent:
            flash("Kind nicht gefunden.", "error")
        else:
            book_points(child, form.delta.data, form.reason.data, kind="manual", actor=current_user)
            db.session.commit()
            flash(
                f"{form.delta.data:+d} Punkte für {child.display_name} gebucht.",
                "success",
            )
            return redirect(url_for("admin.points"))
    recent = (
        PointTransaction.query.order_by(PointTransaction.created_at.desc()).limit(30).all()
    )
    return render_template("admin/points.html", form=form, kids=kids, recent=recent)


@bp.route("/kind/<int:child_id>")
@login_required
@parent_required
def child_detail(child_id):
    child = db.get_or_404(User, child_id)
    if child.is_parent:
        abort(404)
    transactions = (
        PointTransaction.query.filter_by(child_id=child.id)
        .order_by(PointTransaction.created_at.desc())
        .limit(100)
        .all()
    )
    completions = (
        TaskCompletion.query.filter_by(child_id=child.id)
        .order_by(TaskCompletion.submitted_at.desc())
        .limit(50)
        .all()
    )
    redemptions = (
        Redemption.query.filter_by(child_id=child.id)
        .order_by(Redemption.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template(
        "admin/child_detail.html",
        child=child,
        transactions=transactions,
        completions=completions,
        redemptions=redemptions,
    )
