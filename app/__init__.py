import os
from datetime import date

from flask import Flask, abort, flash, redirect, send_from_directory, url_for
from flask_login import current_user

from app.config import Config
from app.extensions import csrf, db, login_manager, migrate


def create_app(test_config=None):
    app = Flask(__name__, template_folder="templates", static_folder="../assets", static_url_path="/assets")
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL is required. Copy .env.example to .env and configure MySQL.")

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db, directory=os.path.join(os.path.dirname(__file__), "migrations"))
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to access that page."
    login_manager.login_message_category = "warning"

    from app.models import User
    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    from app.routes.chat import chat_bp
    from app.routes.main import main_bp
    from app.routes.profile import profile_bp
    from app.routes.rides import rides_bp
    from app.routes.support import support_bp

    @login_manager.user_loader
    def load_user(user_id):
        try:
            user = db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None
        return user if user and not user.is_suspended else None

    @app.before_request
    def reject_suspended_users():
        if current_user.is_authenticated and current_user.is_suspended:
            from flask_login import logout_user

            logout_user()
            flash("This account is unavailable. Contact support for assistance.", "danger")
            return redirect(url_for("auth.login"))

    @app.context_processor
    def template_globals():
        return {"today": date.today()}

    @app.get("/uploads/<path:filename>")
    def uploaded_file(filename):
        safe_name = os.path.basename(filename)
        if not safe_name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            abort(404)
        return send_from_directory(app.config["UPLOAD_FOLDER"], safe_name)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(rides_bp, url_prefix="/rides")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(support_bp, url_prefix="/support")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.errorhandler(413)
    def file_too_large(_error):
        flash("The upload is larger than the 2 MB limit.", "danger")
        return redirect(url_for("profile.profile"))

    return app