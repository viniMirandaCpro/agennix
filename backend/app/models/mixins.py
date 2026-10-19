"""Mixins reutilizaveis pelos modelos (TimestampMixin, TenantMixin)."""
from sqlalchemy import func

from app.extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class TenantMixin:
    tenant_id = db.Column(db.BigInteger, db.ForeignKey("tenants.id"), nullable=False, index=True)
