"""Resolucao e aplicacao do tenant.

Toda query de negocio passa por aqui para nunca vazar dados de outro estabelecimento.
"""
from flask_login import current_user
from flask_restful import abort

from app.extensions import db
from app.models import Tenant


def scoped(model, tenant_id=None):
    """Query do modelo filtrada pelo tenant (do usuario logado, se nao informado)."""
    return model.query.filter_by(tenant_id=tenant_id or current_user.tenant_id)


def get_owned(model, obj_id, tenant_id=None):
    """Busca por id dentro do tenant; registro de outro tenant vira 404."""
    obj = db.session.get(model, obj_id)
    if obj is None or obj.tenant_id != (tenant_id or current_user.tenant_id):
        abort(404, message="Registro não encontrado")
    return obj


def tenant_by_slug(slug):
    tenant = Tenant.query.filter_by(slug=slug, active=True).first()
    if tenant is None:
        abort(404, message="Estabelecimento não encontrado")
    return tenant
