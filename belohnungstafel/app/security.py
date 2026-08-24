from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def parent_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_parent:
            abort(403)
        return view(*args, **kwargs)

    return wrapper


def child_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.is_parent:
            flash("Diese Ansicht ist für die Kinder – hier geht es zur Verwaltung.", "info")
            return redirect(url_for("admin.dashboard"))
        return view(*args, **kwargs)

    return wrapper
