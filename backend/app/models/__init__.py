"""Modelos do dominio.

O desenho completo (diagrama ER, dicionario de dados, constraints e
rastreabilidade com os criterios de aceitacao) esta em docs/modelagem.md.

19 tabelas, distribuidas em 17 modulos - package.py, client_package.py e
professional.py declaram mais de uma tabela cada:

    tenant.py           tenants
    user.py             users
    client.py           clients
    professional.py     professionals, professional_services
    service.py          services
    appointment.py      appointments
    working_hours.py    working_hours
    time_off.py         time_off
    payment.py          payments
    expense.py          expenses
    package.py          packages, package_items
    client_package.py   client_packages, client_package_items
    plan.py             plans            <- unica sem tenant_id
    subscription.py     subscriptions
    api_key.py          api_keys
    notification.py     notifications

TODO: importar todos os modelos aqui para que o Alembic/Flask-Migrate os
enxergue ao gerar as migracoes. Exemplo:

    from app.models.tenant import Tenant
    from app.models.user import User
    ...
"""
