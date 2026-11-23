"""Historia 5.3 (lembretes por SMS) e criterio 3 da 5.12 (confirmacao por SMS)."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Appointment, Client, Notification
from app.services.sms_service import message_for, send_sms
from tests.test_appointments import book
from tests.test_public_booking import public_book

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


class FakeResponse:
    def __init__(self, ok, payload):
        self.ok, self._payload, self.text = ok, payload, str(payload)

    def json(self):
        return self._payload


@pytest.fixture
def twilio(app, monkeypatch):
    """Credenciais de mentira e requests.post gravando as chamadas."""
    app.config.update(TWILIO_ACCOUNT_SID="AC1", TWILIO_AUTH_TOKEN="tok", TWILIO_FROM_NUMBER="+15550001111")
    calls, reply = [], {"response": FakeResponse(True, {"sid": "SM123"})}

    def fake_post(url, **kw):
        calls.append((url, kw))
        return reply["response"]

    monkeypatch.setattr("app.services.sms_service.requests.post", fake_post)
    return calls, reply


def test_send_sms_posts_to_twilio(twilio):
    calls, _ = twilio
    assert send_sms("+5511987654321", "oi") == "SM123"
    url, kw = calls[0]
    assert url == "https://api.twilio.com/2010-04-01/Accounts/AC1/Messages.json"
    assert kw["auth"] == ("AC1", "tok")
    assert kw["data"] == {"From": "+15550001111", "To": "+5511987654321", "Body": "oi"}
    assert kw["timeout"] == 10


def test_send_sms_raises_twilio_error(twilio):
    _, reply = twilio
    reply["response"] = FakeResponse(False, {"message": "The number is unverified"})
    with pytest.raises(RuntimeError, match="unverified"):
        send_sms("+5511987654321", "oi")


def test_send_sms_without_credentials(twilio, app):
    calls, _ = twilio
    app.config.update(TWILIO_ACCOUNT_SID="")
    with pytest.raises(RuntimeError, match="Twilio não configurado"):
        send_sms("+5511987654321", "oi")
    assert calls == []


def test_message_has_five_fields_without_accents(tenant, professional, service, customer):
    tenant.name, professional.name, customer.name = "Barbearia São Jorge", "João", "Ana Lúcia"
    appt = make_appt(tenant, professional, service, customer, datetime(2026, 11, 30, 13, 0, tzinfo=timezone.utc))
    assert message_for(notify(appt, "confirmacao")) == (
        "Barbearia Sao Jorge: Ola Ana, seu horario de Corte com Joao esta confirmado para 30/11 as 10:00."
    )
    assert message_for(notify(appt, "lembrete")) == (
        "Barbearia Sao Jorge: Ola Ana, lembrete: Corte com Joao em 30/11 as 10:00."
    )


def test_message_uses_tenant_timezone(tenant, professional, service, customer):
    appt = make_appt(tenant, professional, service, customer, datetime(2026, 12, 1, 2, 30, tzinfo=timezone.utc))
    assert message_for(notify(appt, "lembrete")).endswith("em 30/11 as 23:30.")


def test_public_booking_queues_confirmation(client, professional, service):
    assert public_book(client, professional, service).status_code == 201
    n = Notification.query.one()
    assert (n.type, n.channel, n.status, n.destination, n.attempts) == (
        "confirmacao", "sms", "pendente", "+5511987654321", 0
    )


def test_panel_booking_has_no_confirmation(auth_client, professional, service, customer):
    assert book(auth_client, professional, service, customer).status_code == 201
    assert Notification.query.count() == 0


def test_conflicting_public_booking_leaves_no_notification(client, professional, service):
    assert public_book(client, professional, service).status_code == 201
    assert public_book(client, professional, service, whatsapp="11912345678").status_code == 409
    assert Notification.query.count() == 1
