"""Alembic environment: uses the same DATABASE_URL and models as the app.

First time:   alembic revision --autogenerate -m "initial tables"
              alembic upgrade head
After you change a model in app/models/entities.py, repeat both commands.
TODO(INTEGRATION: DATABASE): when moving to PostgreSQL, set DATABASE_URL in .env, set
AUTO_CREATE_TABLES=false, then run `alembic upgrade head` on the new database.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.database import Base
from app import models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata,
                      literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.",
                                     poolclass=pool.NullPool)
    with connectable.connect() as connection:
        # render_as_batch lets SQLite handle ALTER TABLE changes
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
