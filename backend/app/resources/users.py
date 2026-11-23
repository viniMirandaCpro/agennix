"""Logins do painel e seus perfis (Historia 5.5). So o administrador acessa.

Perfil profissional exige vinculo com um profissional (professionals.user_id).
ponytail: sem UNIQUE em professionals.user_id - checado aqui; tela so do admin, corrida desprezivel.
"""
from flask_login import current_user, login_required
from flask_restful import Resource, abort

from app.auth.rbac import roles_required
from app.extensions import db
from app.models import Professional, User
from app.schemas import json_body
from app.schemas.user import dump_user, load_user
from app.utils.tenant import get_owned, scoped


def _apply(user, data):
    professional_id = data.pop("professional_id", None)
    password = data.pop("password", None)
    if user.id == current_user.id and (
        data.get("role", user.role) != user.role or data.get("active") is False
    ):
        abort(400, message="Você não pode mudar o próprio perfil nem se desativar")
    if data.get("email", user.email) != user.email and User.query.filter_by(email=data["email"]).first():
        abort(409, message="E-mail já cadastrado")
    for field, value in data.items():
        setattr(user, field, value)
    if password:
        user.set_password(password)

    if user.role != "profissional":
        professional = None
    elif professional_id is not None:
        professional = get_owned(Professional, professional_id)
    else:
        professional = user.professional
    if user.role == "profissional" and professional is None:
        abort(400, message="Escolha o profissional vinculado a este login")
    if professional and professional.user_id not in (None, user.id):
        abort(409, message="Este profissional já tem login")
    user.professional = professional  # trocar ou limpar desfaz o vinculo anterior


class UserList(Resource):
    # login_required por fora: roda antes do teste de perfil
    method_decorators = [roles_required("administrador"), login_required]

    def get(self):
        return [dump_user(u) for u in scoped(User).order_by(User.name)]

    def post(self):
        user = User(tenant_id=current_user.tenant_id)
        _apply(user, load_user(json_body()))
        db.session.add(user)
        db.session.commit()
        return dump_user(user), 201


class UserItem(Resource):
    method_decorators = [roles_required("administrador"), login_required]

    def put(self, user_id):
        user = get_owned(User, user_id)
        _apply(user, load_user(json_body(), partial=True))
        db.session.commit()
        return dump_user(user)
