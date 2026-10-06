"""Instancias das extensoes Flask, criadas sem app (padrao factory).

TODO: declarar aqui as instancias e inicializa-las no create_app:

    db            = SQLAlchemy()
    migrate       = Migrate()
    login_manager = LoginManager()
    cors          = CORS()
    api           = Api()

Atencao ao CORS: o painel Next.js envia o cookie de sessao, entao e
obrigatorio supports_credentials=True com a origem explicita
(http://localhost:3000). Curinga "*" nao funciona junto de credenciais.
"""
