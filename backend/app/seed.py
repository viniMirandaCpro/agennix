"""`flask seed`: cria o estabelecimento de demonstracao. Idempotente pelo slug."""
from decimal import Decimal

import click

from app.extensions import db
from app.models import Professional, Service, Tenant, User
from app.models.working_hours import default_week


@click.command("seed")
def seed_command():
    if Tenant.query.filter_by(slug="demo").first():
        click.echo("Seed ja aplicado (tenant 'demo' existe).")
        return

    tenant = Tenant(name="Barbearia Demo", slug="demo", segment="barbearia")
    db.session.add(tenant)
    db.session.flush()

    admin = User(tenant_id=tenant.id, name="Administrador", email="admin@agennix.dev")
    admin.set_password("agennix123")
    db.session.add(admin)

    for name in ("Carlos", "Marina"):
        db.session.add(
            Professional(tenant_id=tenant.id, name=name, working_hours=default_week(tenant.id))
        )
    for name, minutes, price in (
        ("Corte", 30, "45.00"),
        ("Barba", 30, "35.00"),
        ("Corte + Barba", 60, "70.00"),
    ):
        db.session.add(
            Service(tenant_id=tenant.id, name=name, duration_minutes=minutes, price=Decimal(price))
        )

    db.session.commit()
    click.echo("Seed aplicado: login admin@agennix.dev / agennix123, link publico /agendar/demo")
