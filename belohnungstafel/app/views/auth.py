from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..forms import LoginForm, PasswordChangeForm
from ..models import User

bp = Blueprint("auth", __name__)


def home_for(user):
    return url_for("admin.dashboard") if user.is_parent else url_for("kid.dashboard")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(home_for(current_user))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip().lower()).first()
        if user is None or not user.check_password(form.password.data):
            flash("Benutzername oder Passwort ist falsch.", "error")
        elif not user.enabled:
            flash("Dieses Konto ist gesperrt.", "error")
        else:
            login_user(user, remember=form.remember.data)
            next_url = request.args.get("next", "")
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(home_for(user))
    return render_template("auth/login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Du bist abgemeldet.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/passwort", methods=["GET", "POST"])
@login_required
def change_password():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Das aktuelle Passwort stimmt nicht.", "error")
        else:
            current_user.set_password(form.password.data)
            db.session.commit()
            flash("Passwort geändert.", "success")
            return redirect(home_for(current_user))
    return render_template("auth/change_password.html", form=form)
