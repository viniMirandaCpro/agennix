"""Historia 5.5: perfis de acesso (administrador, atendente, profissional) e cadastro de usuarios."""
from datetime import date, time, timedelta

import pytest

from app.extensions import db
from app.models import Appointment, Client, Professional, Tenant, User
from app.services.appointment_service import local_datetime
from tests.conftest import FUTURE_DAY, PASSWORD

APPOINTMENTS = f"/api/appointments?start={FUTURE_DAY}&end={FUTURE_DAY}"


def make_user(tenant, email, role, professional=None):
    u = User(tenant_id=tenant.id, name=email.split("@")[0], email=email, role=role, professional=professional)
    u.set_password(PASSWORD)
    db.session.add(u)
    db.session.commit()
    return u


def login_as(http, email):
    return http.post("/api/auth/login", json={"email": email, "password": PASSWORD})


@pytest.fixture
def two_appointments(tenant, professional, service):
    """Um agendamento de Maria com o Joao (fixture professional) e um de Pedro com a Ana."""
    ana = Professional(tenant_id=tenant.id, name="Ana")
    start = local_datetime(tenant, date.fromisoformat(FUTURE_DAY), time(10))
    for prof, name, phone in ((professional, "Maria", "+5511999990001"), (ana, "Pedro", "+5511999990002")):
        db.session.add(
            Appointment(
                tenant_id=tenant.id,
                client=Client(tenant_id=tenant.id, name=name, whatsapp=phone),
                professional=prof,
                service=service,
                starts_at=start,
                ends_at=start + timedelta(minutes=30),
                price_charged=service.price,
            )
        )
    db.session.commit()
    return Appointment.query.order_by(Appointment.id).all()


def new_user(**overrides):
    body = {"name": "Bia", "email": "bia@teste.dev", "password": PASSWORD, "role": "atendente"}
    body.update(overrides)
    return body


def test_users_requires_session(client):
    assert client.get("/api/users").status_code == 401


def test_attendant_manages_agenda_but_not_settings(client, tenant, professional, service):
    make_user(tenant, "atendente@teste.dev", "atendente")
    assert login_as(client, "atendente@teste.dev").status_code == 200

    r = client.post(
        "/api/appointments",
        json={
            "professional_id": professional.id,
            "service_id": service.id,
            "date": FUTURE_DAY,
            "time": "10:00",
            "client": {"name": "Jose", "whatsapp": "(11) 91234-5678"},
        },
    )
    assert r.status_code == 201
    assert client.get("/api/services").status_code == 200
    assert client.post("/api/services", json={"name": "X", "duration_minutes": 30, "price": 1}).status_code == 403
    assert client.put(f"/api/professionals/{professional.id}", json={"name": "x"}).status_code == 403
    assert client.get("/api/users").status_code == 403


def test_professional_sees_only_own_appointments_and_clients(client, tenant, professional, two_appointments):
    make_user(tenant, "joao@teste.dev", "profissional", professional)
    login_as(client, "joao@teste.dev")

    assert [a["client"]["name"] for a in client.get(APPOINTMENTS).json] == ["Maria"]
    assert [c["name"] for c in client.get("/api/clients").json] == ["Maria"]
    # Filtro de outro profissional na URL nao fura a restricao
    other = two_appointments[1].professional_id
    assert client.get(f"{APPOINTMENTS}&professional_id={other}").json == []


def test_professional_agenda_is_read_only(client, tenant, professional, service, two_appointments):
    make_user(tenant, "joao@teste.dev", "profissional", professional)
    login_as(client, "joao@teste.dev")

    own = two_appointments[0]
    assert client.put(f"/api/appointments/{own.id}", json={"status": "concluido"}).status_code == 403
    r = client.post(
        "/api/appointments",
        json={"professional_id": professional.id, "service_id": service.id, "date": FUTURE_DAY,
              "time": "15:00", "client_id": own.client_id},
    )
    assert r.status_code == 403


def test_professional_without_link_sees_nothing(client, tenant, two_appointments):
    make_user(tenant, "solto@teste.dev", "profissional")
    login_as(client, "solto@teste.dev")
    assert client.get(APPOINTMENTS).json == []
    assert client.get("/api/clients").json == []


def test_admin_creates_attendant_who_can_login(auth_client):
    r = auth_client.post("/api/users", json=new_user(email="  Bia@Teste.dev "))
    assert r.status_code == 201
    assert r.json["email"] == "bia@teste.dev" and r.json["role"] == "atendente"
    assert [u["email"] for u in auth_client.get("/api/users").json] == ["admin@teste.dev", "bia@teste.dev"]

    auth_client.post("/api/auth/logout")
    assert login_as(auth_client, "bia@teste.dev").status_code == 200


def test_create_user_validation(auth_client):
    assert auth_client.post("/api/users", json={}).status_code == 400
    assert auth_client.post("/api/users", json=new_user(email="sem-arroba")).status_code == 400
    assert auth_client.post("/api/users", json=new_user(password="curta")).status_code == 400
    assert auth_client.post("/api/users", json=new_user(role="dono")).status_code == 400
    assert auth_client.post("/api/users", json=new_user(email="ADMIN@teste.dev")).status_code == 409


def test_professional_user_requires_free_professional(auth_client, professional):
    assert auth_client.post("/api/users", json=new_user(role="profissional")).status_code == 400

    r = auth_client.post("/api/users", json=new_user(role="profissional", professional_id=professional.id))
    assert r.status_code == 201
    assert r.json["professional"] == {"id": professional.id, "name": "Joao"}
    assert professional.user_id == r.json["id"]

    r = auth_client.post(
        "/api/users", json=new_user(email="outro@teste.dev", role="profissional", professional_id=professional.id)
    )
    assert r.status_code == 409


def test_changing_role_unlinks_professional(auth_client, professional):
    uid = auth_client.post(
        "/api/users", json=new_user(role="profissional", professional_id=professional.id)
    ).json["id"]
    r = auth_client.put(f"/api/users/{uid}", json={"role": "atendente"})
    assert r.status_code == 200 and r.json["professional"] is None
    db.session.refresh(professional)
    assert professional.user_id is None


def test_admin_cannot_demote_or_deactivate_self(auth_client, admin):
    assert auth_client.put(f"/api/users/{admin.id}", json={"active": False}).status_code == 400
    assert auth_client.put(f"/api/users/{admin.id}", json={"role": "atendente"}).status_code == 400
    assert auth_client.put(f"/api/users/{admin.id}", json={"name": "Chefe"}).status_code == 200


def test_deactivated_user_cannot_login(auth_client):
    uid = auth_client.post("/api/users", json=new_user()).json["id"]
    assert auth_client.put(f"/api/users/{uid}", json={"active": False, "password": ""}).status_code == 200
    auth_client.post("/api/auth/logout")
    assert login_as(auth_client, "bia@teste.dev").status_code == 401


def test_other_tenant_user_is_404(auth_client):
    other = Tenant(name="Outra", slug="outra")
    db.session.add(other)
    db.session.commit()
    u = make_user(other, "fora@teste.dev", "atendente")
    assert auth_client.put(f"/api/users/{u.id}", json={"name": "x"}).status_code == 404
    assert "fora@teste.dev" not in [x["email"] for x in auth_client.get("/api/users").json]
