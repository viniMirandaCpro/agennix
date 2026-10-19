"""Entrada/saida do recurso 'appointment'.

Data e hora chegam separadas e locais ("2026-10-20", "14:30"); o fuso e o do tenant.
"""
from zoneinfo import ZoneInfo

from flask_restful import abort

from app.models.appointment import STATUSES
from app.schemas import parse_date, parse_int, parse_time
from app.schemas.client import dump_client

REQUIRED = ("professional_id", "service_id", "date", "time")


def dump_appointment(a, tenant):
    tz = ZoneInfo(tenant.timezone)
    start, end = a.starts_at.astimezone(tz), a.ends_at.astimezone(tz)
    return {
        "id": a.id,
        "status": a.status,
        "source": a.source,
        "starts_at": start.isoformat(),
        "ends_at": end.isoformat(),
        "date": start.date().isoformat(),
        "time": start.strftime("%H:%M"),
        "price_charged": str(a.price_charged),
        "notes": a.notes,
        "cancellation_reason": a.cancellation_reason,
        "client": dump_client(a.client),
        "professional": {"id": a.professional.id, "name": a.professional.name},
        "service": {
            "id": a.service.id,
            "name": a.service.name,
            "duration_minutes": a.service.duration_minutes,
        },
    }


def load_appointment(data, partial=False):
    if not partial:
        missing = [f for f in REQUIRED if data.get(f) in (None, "")]
        if not data.get("client_id") and not data.get("client"):
            missing.append("client")
        if missing:
            abort(400, message="Campos obrigatórios ausentes: " + ", ".join(missing), fields=missing)

    out = {"confirm_past": bool(data.get("confirm_past"))}
    for field in ("professional_id", "service_id", "client_id"):
        if data.get(field) not in (None, ""):
            out[field] = parse_int(data[field], field)
    if "date" in data:
        out["date"] = parse_date(data["date"], "date")
    if "time" in data:
        out["time"] = parse_time(data["time"], "time")
    if data.get("client") and "client_id" not in out:
        c = data["client"] if isinstance(data["client"], dict) else {}
        out["client"] = {"name": c.get("name"), "whatsapp": c.get("whatsapp")}
    if "notes" in data:
        out["notes"] = data["notes"] or None
    if "status" in data:
        if data["status"] not in STATUSES:
            abort(400, message="Status inválido")
        out["status"] = data["status"]
    if "cancellation_reason" in data:
        out["cancellation_reason"] = (data["cancellation_reason"] or "")[:255] or None
    return out
