"""Bootstrap missing PostgreSQL tables; never seed or replace application data.

Runs once per backend build, not on requests. Existing schema changes require
an explicit migration; this is only the bootstrap for a new Neon database.
"""
from sqlalchemy import text

from app import create_app, db


def initialize_schema():
    app = create_app()
    with app.app_context():
        if db.engine.dialect.name != 'postgresql':
            raise RuntimeError('Deployment requires a PostgreSQL DATABASE_URL.')
        with db.engine.begin() as connection:
            # Serialize concurrent builds that target the same database.
            connection.execute(text('SET LOCAL lock_timeout = \'60s\''))
            connection.execute(text('SELECT pg_advisory_xact_lock(461928175)'))
            db.metadata.create_all(bind=connection)
        print('Database schema ready. Existing rows preserved; no demo accounts created.')


if __name__ == '__main__':
    try:
        initialize_schema()
    except Exception:
        # Driver errors can contain the DSN. Never include it in build output.
        raise SystemExit('Database setup failed. Check DATABASE_URL, SECRET_KEY, '
                         'JWT_SECRET_KEY, database availability and schema permissions.') from None
