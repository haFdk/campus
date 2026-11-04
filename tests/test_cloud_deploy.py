import os
import unittest
from unittest.mock import patch

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app import create_app, db
from app.config import database_uri, validate_vercel_config
from app.models import User
from deploy_db import initialize_schema


class CloudDeployTests(unittest.TestCase):
    def test_postgres_url_keeps_ssl_options_and_password(self):
        url = 'postgres://user:encoded%40password@host/db?sslmode=require&channel_binding=require'
        with patch.dict(os.environ, {'DATABASE_URL': url}):
            self.assertEqual(database_uri(), url.replace('postgres://', 'postgresql://', 1))

    def test_vercel_rejects_local_database_and_development_keys(self):
        config = {'SQLALCHEMY_DATABASE_URI': 'sqlite://', 'SECRET_KEY': 's' * 64,
                  'JWT_SECRET_KEY': 'j' * 64}
        with patch.dict(os.environ, {'VERCEL': '1'}):
            with self.assertRaisesRegex(RuntimeError, 'DATABASE_URL'):
                validate_vercel_config(config)
            config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@host/db'
            validate_vercel_config(config)
            config['JWT_SECRET_KEY'] = 'dev-only-jwt-secret-change-me'
            with self.assertRaisesRegex(RuntimeError, 'JWT_SECRET_KEY'):
                validate_vercel_config(config)

    def test_current_password_hash_fits_postgresql_column(self):
        user = User(email='test@example.com', nickname='test')
        user.set_password('test-password')
        self.assertLessEqual(len(user.password_hash), User.password_hash.type.length)
        self.assertTrue(user.check_password('test-password'))
        for table in db.metadata.sorted_tables:
            self.assertTrue(str(CreateTable(table).compile(dialect=postgresql.dialect())))

    def test_cloud_initializer_refuses_sqlite_without_creating_tables(self):
        app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
        with patch('deploy_db.create_app', return_value=app):
            with self.assertRaisesRegex(RuntimeError, 'PostgreSQL'):
                initialize_schema()
        with app.app_context():
            from sqlalchemy import inspect
            self.assertEqual(inspect(db.engine).get_table_names(), [])
