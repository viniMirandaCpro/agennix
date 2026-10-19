"""Entrada/saida do agendamento publico: so o necessario, nada de dados de outros clientes."""
from zoneinfo import ZoneInfo

from app.schemas import parse_date, parse_int, parse_time, require


def dump_public_info(tenant, services, professionals):
    return {
        "tenant": {"name": tenant.name, "slug": tenant.slug, "timezone": tenant.timezone},
        "services": [
            {"id": s.id, "name": s.name, "duration_minutes": s.duration_minutes, "price": str(s.price)}
            for s in services
        ],
        "professionals": [{"id": p.id, "name": p.nickname or p.name} for p in professionals],
    }


def dump_public_booking(appt, tenant):
    start = appt.starts_at.astimezone(ZoneInfo(tenant.timezone))
    return {
        "id": appt.id,
        "date": start.date().isoformat(),
        "time": start.strftime("%H:%M"),
        "service": appt.service.name,
        "professional": appt.professional.nickname or appt.professional.name,
        "price": str(appt.price_charged),
        "tenant": tenant.name,
    }


def load_availability_query(args):
    require(args, "service_id", "professional_id", "date")
    return (
        parse_int(args["professional_id"], "professional_id"),
        parse_int(args["service_id"], "service_id"),
        parse_date(args["date"], "date"),
    )


def load_public_booking(data):
    require(data, "service_id", "professional_id", "date", "time", "name", "whatsapp")
    return {
        "professional_id": parse_int(data["professional_id"], "professional_id"),
        "service_id": parse_int(data["service_id"], "service_id"),
        "date": parse_date(data["date"], "date"),
        "time": parse_time(data["time"], "time"),
        "name": data["name"],
        "whatsapp": data["whatsapp"],
    }
