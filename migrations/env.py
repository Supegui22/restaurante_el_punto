import logging
from logging.config import fileConfig
import os
import sys

from alembic import context

# Agrega la ruta raíz del proyecto para poder importar app y db
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db  # Asegúrate de tener 'app' y 'db' definidos en app.py

# Alembic Config
config = context.config

# Logging setup
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

# Ejecutamos todo dentro del contexto de la app
with app.app_context():
    # Establece la URL para SQLAlchemy desde el engine
    config.set_main_option(
        'sqlalchemy.url',
        str(db.engine.url).replace('%', '%%')  # Evita errores por %
    )

    target_metadata = db.metadata

    def run_migrations_offline():
        """Run migrations in 'offline' mode."""
        url = config.get_main_option("sqlalchemy.url")
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True
        )

        with context.begin_transaction():
            context.run_migrations()

    def run_migrations_online():
        """Run migrations in 'online' mode."""

        def process_revision_directives(context, revision, directives):
            if getattr(config.cmd_opts, 'autogenerate', False):
                script = directives[0]
                if script.upgrade_ops.is_empty():
                    directives[:] = []
                    logger.info('No changes in schema detected.')

        connectable = db.engine

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                process_revision_directives=process_revision_directives,
                **app.extensions['migrate'].configure_args
            )

            with context.begin_transaction():
                context.run_migrations()

    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
