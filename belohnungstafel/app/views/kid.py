from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import DecisionForm
from ..models import (
    STATUS_APPROVED,
    STATUS_PENDING,
    PointTransaction,
    Redemption,
    Reward,
    Task,
    TaskCompletion,
    book_points,
    local_now,
)
from ..security import child_required

bp = Blueprint("kid", __name__)


@bp.route("/")
@login_required
@child_required
def dashboard():
    tasks = Task.query.filter_by(active=True).order_by(Task.title).all()
    mine = [t for t in tasks if t.is_for(current_user)]
    board = [{"task": t, "open": t.open_for(current_user)} for t in mine]
    pending = (
        TaskCompletion.query.filter_by(child_id=current_user.id, status=STATUS_PENDING)
        .order_by(TaskCompletion.submitted_at.desc())
        .all()
    )
    recent = (
        PointTransaction.query.filter_by(child_id=current_user.id)
        .order_by(PointTransaction.created_at.desc())
        .limit(5)
        .all()
    )
    return render_template(
        "kid/dashboard.html",
        board=board,
        pending=pending,
        recent=recent,
        balance=current_user.balance,
        form=DecisionForm(),
    )


@bp.route("/aufgabe/<int:task_id>/erledigt", methods=["POST"])
@login_required
@child_required
def complete_task(task_id):
    form = DecisionForm()
    if not form.validate_on_submit():
        flash("Ungültige Anfrage.", "error")
        return redirect(url_for("kid.dashboard"))

    task = db.get_or_404(Task, task_id)
    if not task.active or not task.is_for(current_user):
        flash("Diese Aufgabe ist für dich nicht verfügbar.", "error")
        return redirect(url_for("kid.dashboard"))
    if not task.open_for(current_user):
        flash("Diese Aufgabe hast du schon abgehakt.", "info")
        return redirect(url_for("kid.dashboard"))

    completion = TaskCompletion(
        task_id=task.id,
        child_id=current_user.id,
        points=task.points,
        status=STATUS_PENDING if task.requires_approval else STATUS_APPROVED,
    )
    if not task.requires_approval:
        completion.decided_at = local_now()
        db.session.add(completion)
        book_points(current_user, task.points, f"Aufgabe: {task.title}", kind="task")
        flash(f"Super! +{task.points} Punkte für „{task.title}“.", "success")
    else:
        db.session.add(completion)
        flash(f"„{task.title}“ wurde zur Bestätigung eingereicht.", "success")
    db.session.commit()
    return redirect(url_for("kid.dashboard"))


@bp.route("/shop")
@login_required
@child_required
def store():
    rewards = Reward.query.filter_by(active=True).order_by(Reward.cost).all()
    balance = current_user.balance
    open_redemptions = (
        Redemption.query.filter_by(child_id=current_user.id, status=STATUS_PENDING)
        .order_by(Redemption.created_at.desc())
        .all()
    )
    return render_template(
        "kid/store.html",
        rewards=rewards,
        balance=balance,
        open_redemptions=open_redemptions,
        form=DecisionForm(),
    )


@bp.route("/shop/<int:reward_id>/einloesen", methods=["POST"])
@login_required
@child_required
def redeem(reward_id):
    form = DecisionForm()
    if not form.validate_on_submit():
        flash("Ungültige Anfrage.", "error")
        return redirect(url_for("kid.store"))

    reward = db.get_or_404(Reward, reward_id)
    if not reward.active or not reward.in_stock:
        flash("Diese Belohnung ist gerade nicht verfügbar.", "error")
        return redirect(url_for("kid.store"))
    if current_user.balance < reward.cost:
        flash("Dafür reichen deine Punkte noch nicht.", "error")
        return redirect(url_for("kid.store"))

    redemption = Redemption(reward_id=reward.id, child_id=current_user.id, cost=reward.cost)
    db.session.add(redemption)
    # Punkte werden sofort reserviert und bei Ablehnung zurückgebucht.
    book_points(current_user, -reward.cost, f"Wunsch: {reward.title}", kind="reward")
    if reward.stock is not None:
        reward.stock -= 1
    db.session.commit()
    flash(f"„{reward.title}“ ist angefragt – Mama oder Papa geben es frei.", "success")
    return redirect(url_for("kid.store"))


@bp.route("/verlauf")
@login_required
@child_required
def history():
    transactions = (
        PointTransaction.query.filter_by(child_id=current_user.id)
        .order_by(PointTransaction.created_at.desc())
        .limit(100)
        .all()
    )
    completions = (
        TaskCompletion.query.filter_by(child_id=current_user.id)
        .order_by(TaskCompletion.submitted_at.desc())
        .limit(50)
        .all()
    )
    redemptions = (
        Redemption.query.filter_by(child_id=current_user.id)
        .order_by(Redemption.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template(
        "kid/history.html",
        transactions=transactions,
        completions=completions,
        redemptions=redemptions,
        balance=current_user.balance,
    )
