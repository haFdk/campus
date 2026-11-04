import unittest

from app import create_app, db
from app.models import Demand, Item, Skill, User, Transaction, Message, Review


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "JWT_SECRET_KEY": "test-jwt-secret-at-least-32-characters-long",
            "SECRET_KEY": "test-secret",
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            self.owner = self._user("owner@example.com", "发布者")
            self.requester = self._user("requester@example.com", "响应者")
            self.third = self._user("third@example.com", "旁观者")
            db.session.flush()
            self.skill = Skill(
                user_id=self.owner.id,
                title="数据分析辅导",
                description="从数据清洗到可视化完成一轮练习。",
                category="编程",
                service_mode="线上",
                price_type="交换技能",
                status="active",
            )
            self.item = Item(
                user_id=self.owner.id,
                title="机械键盘",
                description="功能正常，支持校内面交。",
                category="电子产品",
                condition="八成新",
                transaction_type="交换",
                exchange_for="显示器支架",
                status="available",
            )
            self.offered_item = Item(
                user_id=self.requester.id,
                title="显示器支架",
                description="单臂气压支架，配件完整。",
                category="电子产品",
                condition="九成新",
                transaction_type="交换",
                exchange_for="键盘",
                status="available",
            )
            self.demand = Demand(
                user_id=self.owner.id,
                type="skill",
                title="求助作品集排版",
                description="需要梳理信息层级和版式。",
                requirements="周末线上沟通",
                category="设计创意",
                budget_type="交换",
                urgency="high",
                status="open",
            )
            db.session.add_all([
                self.skill,
                self.item,
                self.offered_item,
                self.demand,
            ])
            db.session.commit()
            self.owner_id = self.owner.id
            self.requester_id = self.requester.id
            self.third_id = self.third.id
            self.skill_id = self.skill.id
            self.item_id = self.item.id
            self.offered_item_id = self.offered_item.id
            self.demand_id = self.demand.id

        self.owner_headers = self._login("owner@example.com")
        self.requester_headers = self._login("requester@example.com")
        self.third_headers = self._login("third@example.com")

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @staticmethod
    def _user(email, nickname):
        user = User(email=email, nickname=nickname)
        user.set_password("demo123")
        db.session.add(user)
        return user

    def _login(self, username):
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "demo123"},
        )
        self.assertEqual(response.status_code, 200)
        return {"Authorization": f"Bearer {response.json['access_token']}"}

    def test_health_stats_and_route_inventory(self):
        self.assertEqual(self.client.get("/api/v1/health").json["status"], "ok")
        stats = self.client.get("/api/v1/stats").json
        self.assertEqual(stats["users"], 3)
        business_routes = [
            rule for rule in self.app.url_map.iter_rules()
            if rule.rule.startswith("/api/v1")
        ]
        self.assertTrue(business_routes)
        self.assertFalse(any('/skills' in r.rule or '/demands' in r.rule for r in business_routes))
        self.assertNotIn('skills', stats)
        self.assertNotIn('demands', stats)

    def test_user_contract_exposes_compatible_public_names(self):
        profile = self.client.get("/api/v1/auth/me", headers=self.owner_headers)
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json["username"], "发布者")
        self.assertEqual(profile.json["nickname"], "发布者")
        self.assertIn("avatar_url", profile.json)

    def test_owner_can_update_resource_and_other_user_cannot(self):
        path = f"/api/v1/items/{self.item_id}"
        self.assertEqual(self.client.put(path, headers=self.owner_headers, json={"title": "更新键盘"}).status_code, 200)
        self.assertEqual(self.client.put(path, headers=self.requester_headers, json={"title": "越权"}).status_code, 403)
        self.assertEqual(self.client.delete(path, headers=self.third_headers).status_code, 403)
        self.assertEqual(self.client.get(path).json["item"]["title"], "更新键盘")

    def test_list_contract_supports_search_and_both_pagination_names(self):
        response = self.client.get(
            "/api/v1/items",
            query_string={"search": "机械", "page_size": 5},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["total"], 1)
        self.assertEqual(response.json["meta"]["total_items"], 1)
        self.assertEqual(response.json["items"][0]["user"]["username"], "发布者")

    def test_retired_routes_are_unavailable(self):
        for path in ["/skills", "/skills/1", "/skills/1/request_service", "/skills/1/reviews",
                     "/demands", "/demands/1", "/demands/1/responses", "/demands/responses/1/accept"]:
            for method in ["get", "post", "put", "delete"]:
                self.assertEqual(getattr(self.client, method)("/api/v1" + path, headers=self.owner_headers).status_code, 404)

    def test_message_conversation_query_works_with_sqlalchemy_two(self):
        sent = self.client.post(
            "/api/v1/messages",
            headers=self.requester_headers,
            json={"receiver_id": self.owner_id, "content": "你好，想约时间沟通。"},
        )
        self.assertEqual(sent.status_code, 201)
        conversations = self.client.get(
            "/api/v1/messages/conversations",
            headers=self.owner_headers,
        )
        self.assertEqual(conversations.status_code, 200)
        self.assertEqual(
            conversations.json["conversations"][0]["other_user"]["username"],
            "响应者",
        )

    def exchange(self):
        result = self.client.post("/api/v1/transactions/exchange-requests", headers=self.requester_headers,
            json={"target_item_id": self.item_id, "offered_item_id": self.offered_item_id, "message": "周六交换"})
        self.assertEqual(result.status_code, 201)
        return result.json["transaction"]["id"]

    def test_item_lifecycle_review_and_permissions(self):
        tid = self.exchange()
        path = f"/api/v1/transactions/{tid}"
        self.assertEqual(self.client.get(path, headers=self.third_headers).status_code, 403)
        self.assertEqual(self.client.put(path + "/respond", headers=self.requester_headers, json={"action":"accept"}).status_code, 403)
        self.assertEqual(self.client.post(path + "/reviews", headers=self.requester_headers, json={"rating":5}).status_code, 400)
        self.assertEqual(self.client.put(path + "/respond", headers=self.owner_headers, json={"action":"accept"}).status_code, 200)
        self.assertEqual(self.client.put(path + "/complete", headers=self.third_headers).status_code, 403)
        self.assertEqual(self.client.put(path + "/complete", headers=self.requester_headers).status_code, 200)
        for iid in [self.item_id, self.offered_item_id]:
            self.assertEqual(self.client.get(f"/api/v1/items/{iid}").json["item"]["status"], "exchanged")
        result = self.client.post(path + "/reviews", headers=self.requester_headers, json={"rating":5,"comment":"物品很好"})
        self.assertEqual(result.status_code, 201)
        rid = result.json["review"]["id"]
        self.assertEqual(self.client.post(path + "/reviews", headers=self.requester_headers, json={"rating":5}).status_code, 409)
        self.assertEqual(self.client.post(path + "/reviews", headers=self.third_headers, json={"rating":5}).status_code, 403)
        self.assertEqual(self.client.get("/api/v1/reviews/received", headers=self.owner_headers).json["total"], 1)
        self.assertEqual(self.client.get(f"/api/v1/items/{self.item_id}/reviews").json["total"], 1)
        self.assertEqual(self.client.post(f"/api/v1/reviews/{rid}/reply", headers=self.owner_headers, json={"content":"谢谢"}).status_code, 200)
        self.assertEqual(self.client.put(f"/api/v1/reviews/{rid}", headers=self.third_headers, json={"rating":1}).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/v1/items/{self.item_id}", headers=self.owner_headers).status_code, 200)
        self.assertEqual(self.client.get(path, headers=self.owner_headers).status_code, 200)

    def test_retired_records_preserved_but_not_exposed(self):
        with self.app.app_context():
            transaction = Transaction(requester_id=self.requester_id, provider_id=self.owner_id,
                skill_id=self.skill_id, transaction_type="skill_service", status="completed")
            db.session.add(transaction)
            db.session.flush()
            tid = transaction.id
            review = Review(transaction_id=tid, reviewer_id=self.requester_id, reviewee_id=self.owner_id,
                rating=5, review_type="to_provider")
            db.session.add(review)
            db.session.add(Message(sender_id=self.requester_id, receiver_id=self.owner_id, content="历史记录", related_skill_id=self.skill_id))
            db.session.commit()
            rid = review.id
        self.assertEqual(self.client.get("/api/v1/transactions", headers=self.owner_headers).json["total"], 0)
        self.assertEqual(self.client.get("/api/v1/reviews/received", headers=self.owner_headers).json["total"], 0)
        self.assertEqual(self.client.get("/api/v1/messages/unread-count", headers=self.owner_headers).json["unread_count"], 0)
        self.assertEqual(self.client.get("/api/v1/messages/conversations", headers=self.owner_headers).json["conversations"], [])
        self.assertEqual(self.client.get(f"/api/v1/messages/conversation/{self.requester_id}", headers=self.owner_headers).json["items"], [])
        self.assertEqual(self.client.get("/api/v1/stats").json["transactions"], 0)
        self.assertEqual(self.client.get("/api/v1/auth/stats", headers=self.owner_headers).json["transactions_count"], 0)
        for suffix in ["", "/respond", "/complete", "/cancel"]:
            method = self.client.get if not suffix else self.client.put
            self.assertEqual(method(f"/api/v1/transactions/{tid}" + suffix, headers=self.owner_headers).status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/reviews/{rid}").status_code, 404)
        self.assertEqual(self.client.post(f"/api/v1/transactions/{tid}/reviews", headers=self.owner_headers, json={"rating":5}).status_code, 404)
        self.assertEqual(self.client.post("/api/v1/messages", headers=self.owner_headers,
            json={"receiver_id":self.requester_id, "content":"拒绝旧关联", "related_skill_id":self.skill_id}).status_code, 400)
        with self.app.app_context():
            self.assertEqual(Skill.query.count(), 1)
            self.assertEqual(Demand.query.count(), 1)
            self.assertEqual(Transaction.query.count(), 1)
            self.assertEqual(Review.query.count(), 1)
            self.assertIsNone(Message.query.first().read_at)

    def test_register_profile_password_and_logout(self):
        r = self.client.post("/api/v1/auth/register", json={"username":"新同学","email":"new@example.com","password":"demo123"})
        self.assertEqual(r.status_code, 201)
        h = self._login("new@example.com")
        self.assertEqual(self.client.put("/api/v1/auth/profile", headers=h, json={"major":"计算机"}).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/auth/profile", headers=h).json["major"], "计算机")
        self.assertEqual(self.client.put("/api/v1/auth/change-password", headers=h, json={"old_password":"wrong","new_password":"newpass123"}).status_code, 400)
        self.assertEqual(self.client.put("/api/v1/auth/change-password", headers=h, json={"old_password":"demo123","new_password":"newpass123"}).status_code, 200)
        self.assertEqual(self.client.post("/api/v1/auth/logout", headers=h).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/auth/me", headers=h).status_code, 401)
        self.assertEqual(self.client.post("/api/v1/auth/login", json={"username":"new@example.com","password":"newpass123"}).status_code, 200)

    def test_create_items_filters_and_messages(self):
        payload = {"title":"测试书籍","description":"闲置教材","category":"书籍","condition":"九成新","transaction_type":"出售","sale_price":20}
        self.assertIn(self.client.post("/api/v1/items", json=payload).status_code, (401, 422))
        created = self.client.post("/api/v1/items", headers=self.owner_headers, json=payload)
        self.assertEqual(created.status_code, 201)
        iid = created.json["item"]["id"]
        self.assertEqual(self.client.get("/api/v1/items?category=书籍&per_page=1").json["total"], 1)
        self.assertEqual(self.client.get("/api/v1/items/mine", headers=self.owner_headers).json["total"], 2)
        self.assertEqual(self.client.get("/api/v1/items/mine?category=书籍&search=测试", headers=self.owner_headers).json["total"], 1)
        self.assertEqual(self.client.get("/api/v1/items/mine?search=不存在", headers=self.owner_headers).json["total"], 0)
        self.assertEqual(self.client.post("/api/v1/messages", headers=self.requester_headers, json={"receiver_id":self.owner_id,"content":"想看看","related_item_id":iid}).status_code, 201)
        self.assertEqual(self.client.get("/api/v1/messages/unread-count", headers=self.owner_headers).json["unread_count"], 1)
        self.assertEqual(self.client.get(f"/api/v1/messages/conversation/{self.requester_id}", headers=self.owner_headers).json["meta"]["total_items"], 1)
        self.assertEqual(self.client.get("/api/v1/messages/unread-count", headers=self.owner_headers).json["unread_count"], 0)
        self.assertEqual(self.client.get("/api/v1/messages/conversations", headers=self.third_headers).json["conversations"], [])
        self.assertEqual(self.client.delete(f"/api/v1/items/{iid}", headers=self.owner_headers).status_code, 200)

    def test_cancel_and_reject(self):
        tid = self.exchange()
        p = f"/api/v1/transactions/{tid}"
        self.assertEqual(self.client.put(p + "/cancel", headers=self.third_headers).status_code, 403)
        self.assertEqual(self.client.put(p + "/cancel", headers=self.requester_headers).status_code, 200)
        self.assertEqual(self.client.put(p + "/complete", headers=self.owner_headers).status_code, 400)
        tid = self.exchange()
        self.assertEqual(self.client.put(f"/api/v1/transactions/{tid}/respond", headers=self.owner_headers, json={"action":"reject"}).status_code, 200)

    def test_item_exchange_requires_ownership(self):
        created = self.client.post(
            "/api/v1/transactions/exchange-requests",
            headers=self.requester_headers,
            json={
                "target_item_id": self.item_id,
                "offered_item_id": self.offered_item_id,
                "message": "想交换使用。",
            },
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json["transaction"]["type"], "item")

        denied = self.client.post(
            "/api/v1/transactions/exchange-requests",
            headers=self.third_headers,
            json={
                "target_item_id": self.item_id,
                "offered_item_id": self.offered_item_id,
            },
        )
        self.assertEqual(denied.status_code, 403)


if __name__ == "__main__":
    unittest.main()
