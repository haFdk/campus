#!/usr/bin/env python3
"""Create the local database and a small, credible demo dataset."""

from app import create_app, db
from app.models import Item, Message, Review, Transaction, User
from sqlalchemy import inspect, text


DEMO_PASSWORD = "demo123"


def upgrade_legacy_sqlite_schema():
    """Add columns introduced by the rebuild without deleting existing data."""
    if db.engine.dialect.name != "sqlite":
        return

    expected_columns = {
        "skill": {
            "requirements": "TEXT",
        },
        "demand": {
            "requirements": "TEXT",
            "urgency": "VARCHAR(16) NOT NULL DEFAULT 'medium'",
            "deadline": "DATETIME",
        },
        "review": {
            "reply": "TEXT",
            "replied_at": "DATETIME",
        },
    }

    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    statements = []
    for table_name, columns in expected_columns.items():
        if table_name not in table_names:
            continue
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        for column_name, definition in columns.items():
            if column_name not in existing:
                statements.append(
                    f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {definition}'
                )

    if not statements:
        return

    with db.engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    print(f"已兼容升级旧版 SQLite 数据库（新增 {len(statements)} 个字段）。")


def add_user(email, nickname, major, grade):
    user = User(email=email, nickname=nickname, major=major, grade=grade)
    user.set_password(DEMO_PASSWORD)
    db.session.add(user)
    return user


def init_database(config_overrides=None):
    app = create_app(config_overrides)
    with app.app_context():
        db.create_all()
        upgrade_legacy_sqlite_schema()
        if User.query.first():
            print("数据库已有数据，跳过演示数据初始化。")
            return

        users = [
            add_user("linan@example.com", "林安", "计算机科学", "大三"),
            add_user("suyue@example.com", "苏悦", "视觉传达", "大二"),
            add_user("chenmo@example.com", "陈默", "新闻传播", "大四"),
            add_user("jianghe@example.com", "江禾", "外国语言文学", "研一"),
            add_user("zhouxing@example.com", "周行", "电子工程", "大三"),
        ]
        db.session.flush()

        items = [
            Item(
                user=users[0],
                title="机械键盘 87 键",
                description="青轴，功能正常，已清洁消毒，适合宿舍外接电脑使用。",
                category="电子产品",
                condition="八成新",
                exchange_for="降噪耳机或显示器支架",
                transaction_type="交换或出售",
                sale_price=120,
                location_campus="仙林校区",
                location_building="四组团",
            ),
            Item(
                user=users[1],
                title="设计类经典书 6 本",
                description="包含《设计心理学》《写给大家看的设计书》等，少量划线。",
                category="书籍",
                condition="九成新",
                transaction_type="出售",
                sale_price=68,
                location_campus="鼓楼校区",
                location_building="南园",
            ),
            Item(
                user=users[2],
                title="富士拍立得 Mini 11",
                description="毕业季闲置，机器功能正常，附保护套，可按天租借。",
                category="电子产品",
                condition="九成新",
                transaction_type="租赁",
                rental_price_day=12,
                location_campus="仙林校区",
                location_building="新闻传播学院",
            ),
            Item(
                user=users[3],
                title="瑜伽垫与弹力带",
                description="瑜伽垫厚 8mm，附三档弹力带，适合宿舍日常训练。",
                category="运动器材",
                condition="九成新",
                transaction_type="出售",
                sale_price=35,
                location_campus="仙林校区",
                location_building="五组团",
            ),
        ]
        db.session.add_all(items)

        db.session.flush()

        completed = Transaction(
            requester=users[1],
            provider=users[0],
            item=items[0],
            transaction_type="item_purchase",
            status="completed",
            agreed_terms='{"message":"键盘已当面验收。"}',
        )
        accepted = Transaction(
            requester=users[4],
            provider=users[2],
            item=items[2],
            transaction_type="item_rental",
            status="accepted",
            agreed_terms='{"message":"周六下午借用，傍晚归还。"}',
        )
        items[0].status = "sold"
        db.session.add_all([completed, accepted])
        db.session.flush()

        db.session.add(Review(
            transaction=completed,
            reviewer=users[1],
            reviewee=users[0],
            rating=5,
            comment="物品与描述一致，交接很顺利。",
            review_type="to_provider",
        ))
        db.session.add_all([
            Message(
                sender=users[4],
                receiver=users[2],
                content="你好，拍立得周六下午还方便租借吗？",
                related_item_id=items[2].id,
            ),
            Message(
                sender=users[2],
                receiver=users[4],
                content="可以，下午两点在新传院门口交接。",
                related_item_id=items[2].id,
            ),
        ])

        db.session.commit()
        print("演示数据库初始化完成。")
        print(f"演示账号：linan@example.com / {DEMO_PASSWORD}")
        print(f"其他账号使用相同密码：{DEMO_PASSWORD}")


if __name__ == "__main__":
    init_database()
