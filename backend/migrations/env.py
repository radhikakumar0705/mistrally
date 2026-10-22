import logging
from logging.config import fileConfig

from alembic import context
from flask import current_app

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name, disable_existing_loggers=False)
logger = logging.getLogger("alembic.env")

target_db = current_app.extensions["migrate"].db


def get_engine():
    return target_db.engine


config.set_main_option(
    "sqlalchemy.url", get_engine().url.render_as_string(hide_password=False).replace("%", "%%")
)


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_db.metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    conf_args = current_app.extensions["migrate"].configure_args
    with get_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=target_db.metadata, **conf_args)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
