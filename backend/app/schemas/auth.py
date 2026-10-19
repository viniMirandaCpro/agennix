"""Saida do recurso 'auth': usuario logado + estabelecimento."""


def dump_session(user):
    t = user.tenant
    return {
        "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role},
        "tenant": {"id": t.id, "name": t.name, "slug": t.slug, "timezone": t.timezone},
    }
