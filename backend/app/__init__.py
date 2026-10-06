"""Pacote da aplicacao Flask.

TODO: implementar a application factory create_app(config_name):
  1. carregar a configuracao de config.py
  2. inicializar as extensoes de app/extensions.py (db, migrate, login_manager, cors, api)
  3. importar app.models para registrar as tabelas
  4. registrar os recursos via app.resources.register_resources(api)
  5. registrar os handlers de erro de app/utils/errors.py
  6. iniciar o APScheduler de app/tasks/
"""
