"""Regras de negocio de agendamento (Historias 5.2, 5.8 e 5.12).

Choque de horario: checado aqui para dar mensagem amigavel; a garantia e a
constraint EXCLUDE do banco (docs/modelagem.md 4.2).
"""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from flask_restful import abort
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Appointment, Client, Professional, Service
from app.utils.phone import normalize_whatsapp
from app.utils.tenant import get_owned

SLOT_STEP = timedelta(minutes=30)
CONFLICT_MESSAGE = "Profissional já tem agendamento nesse horário"
EXCLUSION_VIOLATION = "23P01"


def local_datetime(tenant, day, at):
    return datetime.combine(day, at, tzinfo=ZoneInfo(tenant.timezone))


def load_refs(tenant_id, professional_id, service_id):
    """Profissional e servico do tenant, ambos ativos."""
    professional = get_owned(Professional, professional_id, tenant_id)
    service = get_owned(Service, service_id, tenant_id)
    if not professional.active or not service.active:
        abort(400, message="Profissional ou serviço inativo")
    return professional, service


def find_or_create_client(tenant_id, name, whatsapp):
    if not isinstance(name, str) or not name.strip():
        abort(400, message="Informe o nome do cliente")
    name = name.strip()
    if len(name) > 120:
        abort(400, message="Nome muito longo (máximo 120 caracteres)")
    number = normalize_whatsapp(whatsapp)
    client = Client.query.filter_by(tenant_id=tenant_id, whatsapp=number).first()
    if client is None:
        client = Client(tenant_id=tenant_id, name=name, whatsapp=number)
        db.session.add(client)
    return client


def has_conflict(tenant_id, professional_id, starts_at, ends_at, exclude_id=None):
    q = Appointment.query.filter(
        Appointment.tenant_id == tenant_id,
        Appointment.professional_id == professional_id,
        Appointment.status != "cancelado",
        Appointment.starts_at < ends_at,
        Appointment.ends_at > starts_at,
    )
    if exclude_id is not None:
        q = q.filter(Appointment.id != exclude_id)
    return db.session.query(q.exists()).scalar()


def _reject_conflict():
    db.session.rollback()  # descarta um cliente novo pendente na mesma transacao
    abort(409, message=CONFLICT_MESSAGE)


def _commit():
    try:
        db.session.commit()
    except IntegrityError as e:
        if getattr(e.orig, "pgcode", None) == EXCLUSION_VIOLATION:
            _reject_conflict()  # corrida: outra gravacao ocupou o horario
        db.session.rollback()
        raise


def create_appointment(tenant, *, professional, service, client, starts_at, source, notes=None, user=None):
    ends_at = starts_at + timedelta(minutes=service.duration_minutes)
    if has_conflict(tenant.id, professional.id, starts_at, ends_at):
        _reject_conflict()
    appt = Appointment(
        tenant_id=tenant.id,
        client=client,
        professional=professional,
        service=service,
        starts_at=starts_at,
        ends_at=ends_at,
        price_charged=service.price,  # snapshot (modelagem 4.1)
        source=source,
        notes=notes,
        created_by_user_id=user.id if user else None,
    )
    db.session.add(appt)
    _commit()
    return appt


def update_appointment(tenant, appt, data):
    now = datetime.now(timezone.utc)
    local = appt.starts_at.astimezone(ZoneInfo(tenant.timezone))
    new_start = local_datetime(
        tenant,
        data.get("date", local.date()),
        data.get("time", local.time().replace(tzinfo=None)),
    )
    professional = (
        get_owned(Professional, data["professional_id"], tenant.id)
        if "professional_id" in data
        else appt.professional
    )
    service = get_owned(Service, data["service_id"], tenant.id) if "service_id" in data else appt.service
    new_status = data.get("status", appt.status)

    moved = (
        new_start != appt.starts_at
        or professional.id != appt.professional_id
        or service.id != appt.service_id
    )
    cancelling = new_status == "cancelado" and appt.status != "cancelado"
    if appt.starts_at < now and (moved or cancelling) and not data["confirm_past"]:
        abort(
            409,
            message="Este agendamento já passou. Confirme para alterar.",
            code="past_requires_confirmation",
        )

    new_end = new_start + timedelta(minutes=service.duration_minutes) if moved else appt.ends_at
    reactivating = appt.status == "cancelado" and new_status != "cancelado"
    if new_status != "cancelado" and (moved or reactivating):
        if has_conflict(tenant.id, professional.id, new_start, new_end, exclude_id=appt.id):
            _reject_conflict()

    if service.id != appt.service_id:
        appt.price_charged = service.price
    appt.professional, appt.service = professional, service
    appt.starts_at, appt.ends_at = new_start, new_end
    if "notes" in data:
        appt.notes = data["notes"]
    if cancelling:
        appt.cancelled_at = now
        appt.cancellation_reason = data.get("cancellation_reason")
    elif reactivating:
        appt.cancelled_at = appt.cancellation_reason = None
    appt.status = new_status
    _commit()
    return appt


def available_slots(tenant, professional, service, day):
    """Inicios livres ("HH:MM") no dia: cabe inteiro num turno, nao colide e e futuro."""
    now = datetime.now(timezone.utc)
    duration = timedelta(minutes=service.duration_minutes)
    day_start = local_datetime(tenant, day, time.min)
    busy = [
        (a.starts_at, a.ends_at)
        for a in Appointment.query.filter(
            Appointment.tenant_id == tenant.id,
            Appointment.professional_id == professional.id,
            Appointment.status != "cancelado",
            Appointment.starts_at < day_start + timedelta(days=1),
            Appointment.ends_at > day_start,
        )
    ]
    slots = []
    for shift in professional.working_hours:
        if shift.weekday != day.weekday():
            continue
        start = local_datetime(tenant, day, shift.start_time)
        shift_end = local_datetime(tenant, day, shift.end_time)
        while start + duration <= shift_end:
            end = start + duration
            if start > now and not any(s < end and e > start for s, e in busy):
                slots.append(start.strftime("%H:%M"))
            start += SLOT_STEP
    return sorted(slots)
