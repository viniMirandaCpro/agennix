"""Application factory."""
from flask import Flask
from flask_restful import Api

from app.extensions import cors, db, login_manager, migrate


def create_app(config_object="config.DevConfig"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    cors.init_app(app, origins=app.config["CORS_ORIGINS"], supports_credentials=True)

    from app import models  # noqa: F401  registra as tabelas
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        user = db.session.get(User, int(user_id))
        return user if user and user.active else None

    @login_manager.unauthorized_handler
    def unauthorized():
        return {"message": "Não autenticado"}, 401

    from app.resources import register_resources

    api = Api(app, prefix="/api")
    register_resources(api)

    from app.seed import seed_command

    app.cli.add_command(seed_command)
    return app
