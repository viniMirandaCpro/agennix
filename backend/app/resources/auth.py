"""Login, logout e dados do usuario autenticado (Historia 5.1).

Login cria sessao (Flask-Login) e mantem o cookie enquanto o usuario navega.
"""
from datetime import datetime, timezone

from flask_login import current_user, login_required, login_user, logout_user
from flask_restful import Resource, abort

from app.extensions import db
from app.models import User
from app.schemas import json_body, require
from app.schemas.auth import dump_session


class Login(Resource):
    def post(self):
        data = json_body()
        require(data, "email", "password")
        if not isinstance(data["email"], str) or not isinstance(data["password"], str):
            abort(400, message="E-mail e senha devem ser texto")
        user = User.query.filter_by(email=data["email"].strip().lower()).first()
        # login_user devolve False para usuario inativo (User.is_active)
        if not user or not user.check_password(data["password"]) or not login_user(user):
            abort(401, message="E-mail ou senha incorretos")
        user.last_login_at = datetime.now(timezone.utc)
        db.session.commit()
        return dump_session(user)


class Logout(Resource):
    method_decorators = [login_required]

    def post(self):
        logout_user()
        return {"message": "Sessão encerrada"}


class Me(Resource):
    method_decorators = [login_required]

    def get(self):
        return dump_session(current_user)
