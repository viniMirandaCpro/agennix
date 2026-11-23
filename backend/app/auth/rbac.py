"""Controle de acesso por perfil (RBAC proprio, Historia 5.5).

Flask-RBAC esta abandonado. O perfil mora em users.role; o decorator vai direto
no metodo do recurso, por dentro do login_required de method_decorators.
"""
from functools import wraps

from flask_login import current_user
from flask_restful import abort


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                abort(403, message="Sem permissão para esta ação")
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def own_professional_id():
    """Perfil profissional: id do profissional vinculado ao login (None se nao houver)."""
    professional = current_user.professional
    return professional.id if professional else None
