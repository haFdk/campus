import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from app import create_app, db
from app.models import User, Skill, Demand, Item, Transaction
from init_db import init_database
from sqlalchemy.pool import NullPool


class InitializationTest(unittest.TestCase):
    def test_fresh_database_and_repeat_initialization(self):
        with tempfile.TemporaryDirectory() as folder:
            config = {'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(Path(folder) / 'fresh.db'), 'SQLALCHEMY_ENGINE_OPTIONS': {'poolclass': NullPool}}
            init_database(config)
            init_database(config)
            app = create_app(config)
            with app.app_context():
                self.assertEqual(User.query.count(), 5)
                self.assertEqual(Item.query.count(), 4)
                self.assertEqual(Skill.query.count(), 0)
                self.assertEqual(Demand.query.count(), 0)
                self.assertEqual(Transaction.query.count(), 2)
                self.assertTrue(all(t.item_id and not t.skill_id and not t.demand_id for t in Transaction.query.all()))
                db.session.remove()
                db.engine.dispose()

    def test_legacy_schema_upgrade_is_idempotent(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / 'legacy.db'
            # Existing records in a database with all legacy relationships.
            config = {'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(file), 'SQLALCHEMY_ENGINE_OPTIONS': {'poolclass': NullPool}}
            app = create_app(config)
            with app.app_context():
                db.create_all()
                user = User(email='preserve@example.com', nickname='Preserve')
                user.set_password('example123')
                db.session.add(user)
                db.session.commit()
                db.session.remove()
                db.engine.dispose()
            with closing(sqlite3.connect(file)) as conn:
                conn.execute('ALTER TABLE review DROP COLUMN reply')
                conn.execute('ALTER TABLE review DROP COLUMN replied_at')
                conn.commit()
            init_database(config)
            init_database(config)
            with closing(sqlite3.connect(file)) as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM user').fetchone()[0], 1)
                self.assertEqual(conn.execute('SELECT email FROM user').fetchone()[0], 'preserve@example.com')
                self.assertIn('reply', [r[1] for r in conn.execute('PRAGMA table_info(review)')])
                self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
