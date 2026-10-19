"""CRUD de profissionais, com o expediente (working_hours) embutido.

O 'working_hours' enviado substitui o expediente inteiro.
"""
from flask_login import current_user, login_required
from flask_restful import Resource

from app.extensions import db
from app.models import Professional, WorkingHours
from app.models.working_hours import default_week
from app.schemas import json_body
from app.schemas.professional import dump_professional, load_professional
from app.utils.tenant import get_owned, scoped


def _apply(p, data):
    rows = data.pop("working_hours", None)
    for field, value in data.items():
        setattr(p, field, value)
    if rows is not None:
        p.working_hours = [
            WorkingHours(tenant_id=p.tenant_id, weekday=wd, start_time=start, end_time=end)
            for wd, start, end in rows
        ]


class ProfessionalList(Resource):
    method_decorators = [login_required]

    def get(self):
        return [dump_professional(p) for p in scoped(Professional).order_by(Professional.name)]

    def post(self):
        tenant_id = current_user.tenant_id
        p = Professional(tenant_id=tenant_id, working_hours=default_week(tenant_id))
        _apply(p, load_professional(json_body()))
        db.session.add(p)
        db.session.commit()
        return dump_professional(p), 201


class ProfessionalItem(Resource):
    method_decorators = [login_required]

    def put(self, professional_id):
        p = get_owned(Professional, professional_id)
        _apply(p, load_professional(json_body(), partial=True))
        db.session.commit()
        return dump_professional(p)
