"""`flask scheduler`: processo proprio que roda o job de SMS a cada minuto.

Fica fora do `flask run` porque o reloader do --debug e cada worker do gunicorn
criariam um agendador a mais, e o mesmo SMS sairia duas vezes.
"""
from datetime import datetime, timezone

import click
from apscheduler.schedulers.blocking import BlockingScheduler
from flask import current_app
from flask.cli import with_appcontext

from app.tasks.reminders import run_once


@click.command("scheduler")
@with_appcontext
def scheduler_command():
    app = current_app._get_current_object()

    def job():  # o APScheduler roda em outra thread, sem o app context do comando
        with app.app_context():
            run_once()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        job,
        "interval",
        minutes=1,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(timezone.utc),
    )
    click.echo("Agendador de SMS rodando a cada minuto.")
    scheduler.start()
