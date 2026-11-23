"""Historia 5.3 (lembretes por SMS) e criterio 3 da 5.12 (confirmacao por SMS)."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Appointment, Client, Notification

NOW = datetime(2026, 11, 30, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def customer(tenant):
    c = Client(tenant_id=tenant.id, name="Maria", whatsapp="+5511987654321")
    db.session.add(c)
    db.session.commit()
    return c


def make_appt(tenant, professional, service, customer, starts_at, *, created_at=None, status="confirmado"):
    a = Appointment(
        tenant_id=tenant.id,
        client=customer,
        professional=professional,
        service=service,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        price_charged=service.price,
        status=status,
        created_at=created_at or starts_at - timedelta(days=1),
    )
    db.session.add(a)
    db.session.commit()
    return a


def notify(appt, type="confirmacao", **kw):
    n = Notification(
        tenant_id=appt.tenant_id,
        appointment=appt,
        type=type,
        channel=kw.pop("channel", "sms"),
        destination=appt.client.whatsapp,
        scheduled_for=kw.pop("scheduled_for", NOW),
        **kw,
    )
    db.session.add(n)
    db.session.commit()
    return n


def test_notification_is_unique_per_appointment_and_type(tenant, professional, service, customer):
    appt = make_appt(tenant, professional, service, customer, NOW + timedelta(hours=1))
    notify(appt, "lembrete")
    with pytest.raises(IntegrityError):
        notify(appt, "lembrete")
    db.session.rollback()


def test_channel_rejects_whatsapp(tenant, professional, service, customer):
    appt = make_appt(tenant, professional, service, customer, NOW + timedelta(hours=1))
    with pytest.raises(IntegrityError):
        notify(appt, channel="whatsapp")
    db.session.rollback()
