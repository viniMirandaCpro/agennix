"""Expediente do profissional: dia da semana e faixa de horario.

Turno partido = duas linhas no mesmo weekday. Base do calculo de horarios livres. Ver docs/modelagem.md secao 3.8.
"""
from datetime import time

from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin


class WorkingHours(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "working_hours"

    id = db.Column(db.BigInteger, primary_key=True)
    professional_id = db.Column(
        db.BigInteger, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    weekday = db.Column(db.SmallInteger, nullable=False)  # 0 = segunda ... 6 = domingo
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    __table_args__ = (
        db.CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_working_hours_weekday"),
        db.CheckConstraint("end_time > start_time", name="ck_working_hours_range"),
    )


def default_week(tenant_id):
    """Expediente inicial de todo profissional novo: segunda a sabado, 09:00-18:00."""
    return [
        WorkingHours(tenant_id=tenant_id, weekday=d, start_time=time(9), end_time=time(18))
        for d in range(6)
    ]
