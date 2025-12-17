from __future__ import annotations

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from flask import current_app

# Alembic Config object
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use Flask SQLAlchemy metadata
target_metadata = current_app.extensions['migrate'].db.metadata

# Inject URL from Flask config (avoids relying on alembic.ini)
sqlalchemy_url = current_app.config.get("SQLALCHEMY_DATABASE_URI")
if sqlalchemy_url:
    config.set_main_option("sqlalchemy.url", sqlalchemy_url)


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

