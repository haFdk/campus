import unittest
from unittest.mock import patch

from flask_jwt_extended import create_access_token
from app import create_app, db
from app.models import User, Item
from app.services.classification import Classifier, ClassificationUnavailable, ClassificationBusy, CATEGORIES


class ClassificationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://',
                               'JWT_SECRET_KEY': 'classification-test-secret-at-least-32-chars'})
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            user = User(email='test@example.com', nickname='test')
            user.set_password('test-password')
            db.session.add(user)
            db.session.commit()
            self.headers = {'Authorization': 'Bearer ' + create_access_token(identity='1')}
        self.service = self.app.extensions['item_classifier']
        self.payload = {'title': '二手蓝牙耳机'}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def post(self, data=None):
        return self.client.post('/api/v1/items/category-suggestion', json=data or self.payload, headers=self.headers)

    def test_requires_auth(self):
        self.assertEqual(self.client.post('/api/v1/items/category-suggestion', json=self.payload).status_code, 422)

    def test_validation(self):
        for data in [[], {'title': 123}, {'title': 'a' * 51}]:
            response = self.client.post('/api/v1/items/category-suggestion', json=data, headers=self.headers)
            self.assertEqual(response.status_code, 400)

    def test_insufficient_does_not_load(self):
        with patch.object(self.service, 'recommend') as mock:
            self.assertEqual(self.post({'title': '   '}).json['status'], 'uncertain')
            mock.assert_not_called()

    def test_title_only_and_legacy_description_ignored(self):
        with patch.object(self.service, 'recommend', return_value={'status': 'uncertain', 'category': None}) as mock:
            for payload in [{'title': '吉他'}, {'title': '吉他', 'description': ''},
                            {'title': '吉他', 'description': '耳机'}, {'title': '吉他', 'description': 42}]:
                self.assertEqual(self.post(payload).status_code, 200)
            self.assertEqual([call.args[0] for call in mock.call_args_list], ['吉他'] * 4)

    def test_recommendation_does_not_write(self):
        ranking = [{'category': '电子产品', 'score': .9, 'support': .95},
                   {'category': '家居用品', 'score': .05, 'support': .1}]
        with patch('app.services.category_lexicon.Lexicon.match', return_value=[]), patch.object(self.service, 'rank', return_value=ranking):
            response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.json['category'], CATEGORIES)
        with self.app.app_context():
            self.assertEqual(Item.query.count(), 0)
            self.assertEqual(User.query.count(), 1)

    def test_uncertain_and_other_are_different(self):
        for category, score, expected in [('其他', .9, 'suggested'), (None, .9, 'uncertain'), ('其他', .3, 'uncertain')]:
            with patch('app.services.category_lexicon.Lexicon.match', return_value=[]), patch.object(self.service, 'rank', return_value=[
                {'category': category, 'score': score, 'support': .95},
                {'category': '服装', 'score': .2, 'support': .1}]):
                self.assertEqual(self.post().json['status'], expected)

    def test_disabled_and_model_absent(self):
        self.app.config['CLASSIFICATION_ENABLED'] = False
        self.assertEqual(self.post().status_code, 503)
        self.assertEqual(self.client.get('/api/v1/health').status_code, 200)
        self.app.config['CLASSIFICATION_ENABLED'] = True
        self.app.config['CLASSIFICATION_MODEL_PATH'] = 'missing-classification-model'
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['source'], 'lexicon')
        self.assertTrue(response.json['degraded'])
        self.assertEqual(self.post({'title': '马赛克'}).status_code, 503)
        self.assertEqual(self.client.get('/api/v1/items').status_code, 200)

    def test_busy_and_lock_release(self):
        self.service.lock.acquire()
        try:
            self.assertEqual(self.post().json['source'], 'lexicon')
            self.assertEqual(self.post({'title': '琴'}).status_code, 429)
        finally:
            self.service.lock.release()
        with patch.object(self.service, '_hybrid', side_effect=RuntimeError('failure')):
            self.assertEqual(self.post().json['source'], 'lexicon')
            self.assertEqual(self.post({'title': '马赛克'}).status_code, 503)
        self.assertFalse(self.service.lock.locked())

    def test_shared_instance_without_eager_load(self):
        self.assertIs(self.service, self.app.extensions['item_classifier'])
        self.assertIsNone(self.service.model)

    def test_deleted_user(self):
        with self.app.app_context():
            db.session.delete(db.session.get(User, 1))
            db.session.commit()
        self.assertEqual(self.post().status_code, 403)

    def test_request_limit_and_live_capability(self):
        response = self.post({'title': '手机', 'description': 'a' * 9000})
        self.assertEqual(response.status_code, 413)
        self.assertIn('category-suggestion-hybrid-v3', self.client.get('/api/v1/health').json['capabilities'])

    def test_no_candidates_for_invalid_input_and_no_database_mutation(self):
        response = self.post({'title': '招聘手机维修师傅'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['candidates'], [])
        with self.app.app_context():
            self.assertEqual(User.query.count(), 1)
            self.assertEqual(Item.query.count(), 0)


if __name__ == '__main__':
    unittest.main()
