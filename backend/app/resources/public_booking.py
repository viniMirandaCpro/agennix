"""Agendamento publico, sem login (Historia 5.12).

Exige apenas nome e WhatsApp; so aceita horarios oferecidos por available_slots.
ponytail: sem rate limit nem captcha - suficiente para demo; adicionar antes de expor na internet.
"""
from flask import request
from flask_restful import Resource, abort

from app.models import Professional, Service
from app.schemas import json_body
from app.schemas.public_booking import (
    dump_public_booking,
    dump_public_info,
    load_availability_query,
    load_public_booking,
)
from app.services.appointment_service import (
    available_slots,
    create_appointment,
    find_or_create_client,
    load_refs,
    local_datetime,
)
from app.utils.tenant import scoped, tenant_by_slug


class PublicInfo(Resource):
    def get(self, slug):
        tenant = tenant_by_slug(slug)
        services = scoped(Service, tenant.id).filter_by(active=True).order_by(Service.name)
        professionals = scoped(Professional, tenant.id).filter_by(active=True).order_by(Professional.name)
        return dump_public_info(tenant, services, professionals)


class PublicAvailability(Resource):
    def get(self, slug):
        tenant = tenant_by_slug(slug)
        professional_id, service_id, day = load_availability_query(request.args)
        professional, service = load_refs(tenant.id, professional_id, service_id)
        return {"date": day.isoformat(), "slots": available_slots(tenant, professional, service, day)}


class PublicBooking(Resource):
    def post(self, slug):
        tenant = tenant_by_slug(slug)
        data = load_public_booking(json_body())
        professional, service = load_refs(tenant.id, data["professional_id"], data["service_id"])
        if data["time"].strftime("%H:%M") not in available_slots(tenant, professional, service, data["date"]):
            abort(409, message="Horário indisponível. Escolha outro horário.")
        client = find_or_create_client(tenant.id, data["name"], data["whatsapp"])
        appt = create_appointment(
            tenant,
            professional=professional,
            service=service,
            client=client,
            starts_at=local_datetime(tenant, data["date"], data["time"]),
            source="publico",
        )
        return dump_public_booking(appt, tenant), 201
