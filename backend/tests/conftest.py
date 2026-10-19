"""Fixtures compartilhadas do pytest.

Roda em Postgres real (TEST_DATABASE_URL): EXCLUDE e tstzrange nao existem no SQLite.
Cada teste recria as tabelas, entao nenhum estado vaza entre testes.
"""
from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.models import Professional, Service, Tenant, User, WorkingHours

PASSWORD = "senha123"
FUTURE_DAY = (date.today() + timedelta(days=7)).isoformat()
PAST_DAY = (date.today() - timedelta(days=7)).isoformat()


@pytest.fixture
def app():
    app = create_app("config.TestConfig")
    with app.app_context():
        db.session.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        db.session.commit()
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def tenant(app):
    t = Tenant(name="Barbearia Teste", slug="teste")
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture
def admin(tenant):
    u = User(tenant_id=tenant.id, name="Admin", email="admin@teste.dev")
    u.set_password(PASSWORD)
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def professional(tenant):
    """Trabalha todos os dias, 09:00-18:00."""
    p = Professional(
        tenant_id=tenant.id,
        name="Joao",
        working_hours=[
            WorkingHours(tenant_id=tenant.id, weekday=d, start_time=time(9), end_time=time(18))
            for d in range(7)
        ],
    )
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture
def service(tenant):
    s = Service(tenant_id=tenant.id, name="Corte", duration_minutes=30, price=Decimal("40.00"))
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture
def auth_client(client, admin):
    r = client.post("/api/auth/login", json={"email": admin.email, "password": PASSWORD})
    assert r.status_code == 200
    return client
