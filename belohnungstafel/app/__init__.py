from flask import Flask
from flask_wtf.csrf import CSRFProtect

from .config import INSTANCE_DIR, Config
from .extensions import db, login_manager

csrf = CSRFProtect()


def create_app(config_object=Config):
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    app = Flask(__name__, instance_path=str(INSTANCE_DIR))
    app.config.from_object(config_object)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401  (Modelle registrieren)
    from .views.admin import bp as admin_bp
    from .views.auth import bp as auth_bp
    from .views.kid import bp as kid_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(kid_bp)
    app.register_blueprint(admin_bp)

    from .cli import register_cli

    register_cli(app)

    with app.app_context():
        db.create_all()

    return app
