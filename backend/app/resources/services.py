"""CRUD de servicos oferecidos (duracao e preco). Desativar = active false."""
from flask_login import current_user, login_required
from flask_restful import Resource

from app.extensions import db
from app.models import Service
from app.schemas import json_body
from app.schemas.service import dump_service, load_service
from app.utils.tenant import get_owned, scoped


class ServiceList(Resource):
    method_decorators = [login_required]

    def get(self):
        return [dump_service(s) for s in scoped(Service).order_by(Service.name)]

    def post(self):
        s = Service(tenant_id=current_user.tenant_id, **load_service(json_body()))
        db.session.add(s)
        db.session.commit()
        return dump_service(s), 201


class ServiceItem(Resource):
    method_decorators = [login_required]

    def put(self, service_id):
        s = get_owned(Service, service_id)
        for field, value in load_service(json_body(), partial=True).items():
            setattr(s, field, value)
        db.session.commit()
        return dump_service(s)
