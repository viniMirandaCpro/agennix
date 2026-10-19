"""CRUD de agendamentos pelo painel (Historias 5.2, 5.8 e 5.4).

Nao ha exclusao fisica: cancelar = PUT com status 'cancelado'.
"""
from datetime import time, timedelta

from flask import request
from flask_login import current_user, login_required
from flask_restful import Resource
from sqlalchemy.orm import joinedload

from app.models import Appointment, Client
from app.schemas import json_body, parse_date, parse_int, require
from app.schemas.appointment import dump_appointment, load_appointment
from app.services.appointment_service import (
    create_appointment,
    find_or_create_client,
    load_refs,
    local_datetime,
    update_appointment,
)
from app.utils.tenant import get_owned, scoped


class AppointmentList(Resource):
    method_decorators = [login_required]

    def get(self):
        tenant = current_user.tenant
        args = request.args
        require(args, "start", "end")
        start = local_datetime(tenant, parse_date(args["start"], "start"), time.min)
        end = local_datetime(tenant, parse_date(args["end"], "end") + timedelta(days=1), time.min)
        q = scoped(Appointment).filter(Appointment.starts_at >= start, Appointment.starts_at < end)
        for field in ("professional_id", "service_id"):
            if args.get(field):
                q = q.filter(getattr(Appointment, field) == parse_int(args[field], field))
        q = q.options(
            joinedload(Appointment.client),
            joinedload(Appointment.professional),
            joinedload(Appointment.service),
        ).order_by(Appointment.starts_at)
        return [dump_appointment(a, tenant) for a in q]

    def post(self):
        tenant = current_user.tenant
        data = load_appointment(json_body())
        professional, service = load_refs(tenant.id, data["professional_id"], data["service_id"])
        if "client_id" in data:
            client = get_owned(Client, data["client_id"], tenant.id)
        else:
            client = find_or_create_client(tenant.id, **data["client"])
        appt = create_appointment(
            tenant,
            professional=professional,
            service=service,
            client=client,
            starts_at=local_datetime(tenant, data["date"], data["time"]),
            source="painel",
            notes=data.get("notes"),
            user=current_user,
        )
        return dump_appointment(appt, tenant), 201


class AppointmentItem(Resource):
    method_decorators = [login_required]

    def put(self, appointment_id):
        tenant = current_user.tenant
        appt = get_owned(Appointment, appointment_id)
        update_appointment(tenant, appt, load_appointment(json_body(), partial=True))
        return dump_appointment(appt, tenant)
