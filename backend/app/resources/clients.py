"""Busca de clientes para o formulario de agendamento.

O cadastro do cliente novo acontece junto com o agendamento (appointment_service).
Perfil profissional (Historia 5.5): so ve quem ja agendou com ele.
"""
import re

from flask import request
from flask_login import current_user, login_required
from flask_restful import Resource
from sqlalchemy import or_, select

from app.auth.rbac import own_professional_id
from app.models import Appointment, Client
from app.schemas.client import dump_client
from app.utils.tenant import scoped


class ClientList(Resource):
    method_decorators = [login_required]

    def get(self):
        query = scoped(Client)
        if current_user.role == "profissional":
            own = select(Appointment.client_id).where(Appointment.professional_id == own_professional_id())
            query = query.filter(Client.id.in_(own))
        q = (request.args.get("q") or "").strip()
        if q:
            # WhatsApp e salvo em E.164: busca so pelos digitos, aceitando "(11) 9123-..."
            digits = re.sub(r"\D", "", q)
            match = Client.name.ilike(f"%{q}%")
            if digits:
                match = or_(match, Client.whatsapp.like(f"%{digits}%"))
            query = query.filter(match)
        return [dump_client(c) for c in query.order_by(Client.name).limit(20)]
