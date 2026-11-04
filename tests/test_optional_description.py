import unittest
from flask_jwt_extended import create_access_token
from app import create_app, db
from app.models import Item, User


class OptionalDescriptionTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://',
                               'JWT_SECRET_KEY': 'optional-description-test-secret-key'})
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            for email in ['a@example.com', 'b@example.com']:
                user = User(email=email, nickname=email)
                user.set_password('test-password')
                db.session.add(user)
            db.session.commit()
            self.owner = {'Authorization': 'Bearer ' + create_access_token(identity='1')}
            self.other = {'Authorization': 'Bearer ' + create_access_token(identity='2')}
        self.base = {'title': '高等数学教材', 'category': '书籍', 'condition': '九成新',
                     'transaction_type': '交换', 'exchange_for': '其他书籍'}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def create(self, **extra):
        return self.client.post('/api/v1/items', json={**self.base, **extra}, headers=self.owner)

    def update(self, item_id, data, headers=None):
        return self.client.put(f'/api/v1/items/{item_id}', json=data, headers=headers or self.owner)

    def test_create_optional_normalization_search_and_filter(self):
        for value in [None, '', '  ']:
            extra = {} if value is None else {'description': value}
            response = self.create(**extra)
            self.assertEqual(response.status_code, 201, response.json)
            item = response.json['item']
            self.assertEqual(item['description'], '')
            self.assertEqual(self.client.get(f"/api/v1/items/{item['id']}").json['item']['description'], '')
        self.assertEqual(self.client.get('/api/v1/items?search=高等数学').json['total'], 3)
        self.assertEqual(self.client.get('/api/v1/items?category=书籍').json['total'], 3)
        self.assertEqual(self.create(description='古旧教材，带笔记').status_code, 201)
        self.assertEqual(self.client.get('/api/v1/items?search=笔记').json['total'], 1)

    def test_update_omitted_preserves_and_explicit_clears(self):
        item = self.create(description='原来的介绍').json['item']
        ident = item['id']
        self.assertEqual(self.update(ident, {'title': '新版教材'}).json['item']['description'], '原来的介绍')
        for value in ['', '  ', None]:
            self.assertEqual(self.update(ident, {'description': '临时介绍'}).status_code, 200)
            result = self.update(ident, {'description': value})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json['item']['description'], '')

    def test_description_validation_and_unchanged_required_fields(self):
        for value in [1, [], {}, '字' * 501]:
            self.assertEqual(self.create(description=value).status_code, 400)
        item = self.create(description='有效内容').json['item']
        for value in [1, [], {}, '字' * 501]:
            self.assertEqual(self.update(item['id'], {'description': value}).status_code, 400)
        self.assertEqual(self.client.get(f"/api/v1/items/{item['id']}").json['item']['description'], '有效内容')
        self.assertEqual(self.client.post('/api/v1/items', json={'title': '无分类'}, headers=self.owner).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/items', json=self.base).status_code, 422)
        self.assertEqual(self.update(item['id'], {'description': ''}, self.other).status_code, 403)


if __name__ == '__main__':
    unittest.main()
