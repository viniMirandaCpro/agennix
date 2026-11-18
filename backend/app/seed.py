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

    carlos, marina = (
        Professional(tenant_id=tenant.id, name=name, working_hours=default_week(tenant.id))
        for name in ("Carlos", "Marina")
    )
    db.session.add_all([carlos, marina])

    # Um login por perfil (Historia 5.5); Carlos ve so a propria agenda
    for name, email, role, professional in (
        ("Administrador", "admin@agennix.dev", "administrador", None),
        ("Atendente", "atendente@agennix.dev", "atendente", None),
        ("Carlos", "carlos@agennix.dev", "profissional", carlos),
    ):
        user = User(tenant_id=tenant.id, name=name, email=email, role=role, professional=professional)
        user.set_password("agennix123")
        db.session.add(user)

    for name, minutes, price in (
        ("Corte", 30, "45.00"),
        ("Barba", 30, "35.00"),
        ("Corte + Barba", 60, "70.00"),
    ):
        db.session.add(
            Service(tenant_id=tenant.id, name=name, duration_minutes=minutes, price=Decimal(price))
        )

    db.session.commit()
    click.echo(
        "Seed aplicado: logins admin@, atendente@ e carlos@agennix.dev / agennix123,"
        " link publico /agendar/demo"
    )
