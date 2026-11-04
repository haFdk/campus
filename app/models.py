# app/models.py
from app import db
from datetime import UTC, datetime
from werkzeug.security import generate_password_hash, check_password_hash


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(64), nullable=False, index=True)
    avatar_url = db.Column(db.String(256), nullable=True)
    major = db.Column(db.String(120), nullable=True)
    grade = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            # username/avatar are the public API names. Keep the original
            # nickname/avatar_url fields for backwards compatibility.
            'username': self.nickname,
            'nickname': self.nickname,
            'avatar': self.avatar_url,
            'avatar_url': self.avatar_url,
            'major': self.major,
            'grade': self.grade,
            'created_at': self.created_at.isoformat() + 'Z',
            'updated_at': self.updated_at.isoformat() + 'Z'
        }

    def to_public_dict(self):
        data = self.to_dict()
        data.pop('email', None)
        data.update({
            'item_count': self.items.count(),
        })
        return data

    def __repr__(self):
        return f'<User {self.nickname}>'

# Legacy storage only: no routes expose or mutate this retired module.
class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(64), nullable=False, index=True)
    service_mode = db.Column(db.String(64), nullable=False)  # e.g., '线上', '线下', '均可'
    price_type = db.Column(db.String(32), nullable=False)  # e.g., '免费', '交换技能', '付费'
    price_amount = db.Column(db.Float, nullable=True)
    currency = db.Column(db.String(10), nullable=True, default='CNY')
    available_times = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), nullable=False, default='active', index=True)  # e.g., 'active', 'inactive', 'completed'
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    user = db.relationship('User', backref=db.backref('skills', lazy='dynamic'))

    def to_dict(self, include_user=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'requirements': self.requirements,
            'category': self.category,
            'service_mode': self.service_mode,
            'price_type': self.price_type,
            'price_amount': self.price_amount,
            'currency': self.currency,
            'available_times': self.available_times,
            'status': self.status,
            'rating': self.average_rating,
            'review_count': self.review_count,
            'created_at': self.created_at.isoformat() + 'Z',
            'updated_at': self.updated_at.isoformat() + 'Z'
        }
        if include_user and self.user:
            data['user'] = self.user.to_public_dict()
        return data

    @property
    def review_count(self):
        return sum(transaction.reviews.count() for transaction in self.transactions)

    @property
    def average_rating(self):
        ratings = [
            review.rating
            for transaction in self.transactions
            for review in transaction.reviews
            if review.reviewee_id == self.user_id
        ]
        return round(sum(ratings) / len(ratings), 1) if ratings else 0

    def __repr__(self):
        return f'<Skill {self.title}>'

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(64), nullable=False, index=True)
    condition = db.Column(db.String(64), nullable=False)  # e.g., '全新', '九成新'
    images = db.Column(db.JSON, nullable=True)  # 存储图片URL列表, e.g., ['url1', 'url2']
    exchange_for = db.Column(db.Text, nullable=True)  # 期望交换的物品描述
    rental_price_day = db.Column(db.Float, nullable=True)
    sale_price = db.Column(db.Float, nullable=True)
    transaction_type = db.Column(db.String(64), nullable=False, index=True)  # e.g., '交换', '租赁', '出售', '交换或出售'
    status = db.Column(db.String(32), nullable=False, default='available', index=True)  # e.g., 'available', 'rented_out', 'sold', 'exchanged', 'unavailable'
    location_campus = db.Column(db.String(120), nullable=True)
    location_building = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    user = db.relationship('User', backref=db.backref('items', lazy='dynamic'))

    def to_dict(self, include_user=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'owner_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'condition': self.condition,
            'images': self.images or [],
            'exchange_for': self.exchange_for,
            'rental_price_day': self.rental_price_day,
            'sale_price': self.sale_price,
            'transaction_type': self.transaction_type,
            'status': self.status,
            'location_campus': self.location_campus,
            'location_building': self.location_building,
            'created_at': self.created_at.isoformat() + 'Z',
            'updated_at': self.updated_at.isoformat() + 'Z'
        }
        if include_user and self.user:
            owner = self.user.to_public_dict()
            data['user'] = owner
            data['owner'] = owner
        return data

    def __repr__(self):
        return f'<Item {self.title}>'

# Legacy storage retained to preserve existing foreign keys and historical data.
class Demand(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    type = db.Column(db.String(32), nullable=False, index=True)  # e.g., 'skill', 'item'
    title = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(64), nullable=True, index=True)
    budget_type = db.Column(db.String(32), nullable=False)  # e.g., '免费', '交换', '付费'
    budget_amount_min = db.Column(db.Float, nullable=True)
    budget_amount_max = db.Column(db.Float, nullable=True)
    currency = db.Column(db.String(10), nullable=True, default='CNY')
    urgency = db.Column(db.String(16), nullable=False, default='medium', index=True)
    deadline = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(32), nullable=False, default='open', index=True)  # e.g., 'open', 'fulfilled', 'closed'
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    user = db.relationship('User', backref=db.backref('demands', lazy='dynamic'))

    def to_dict(self, include_user=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'publisher_id': self.user_id,
            'type': self.type,
            'title': self.title,
            'description': self.description,
            'requirements': self.requirements,
            'category': self.category,
            'budget_type': self.budget_type,
            'budget_amount_min': self.budget_amount_min,
            'budget_amount_max': self.budget_amount_max,
            'currency': self.currency,
            'urgency': self.urgency,
            'deadline': self.deadline.isoformat() + 'Z' if self.deadline else None,
            'status': self.status,
            'response_count': self.transactions.count(),
            'created_at': self.created_at.isoformat() + 'Z',
            'updated_at': self.updated_at.isoformat() + 'Z'
        }
        if include_user and self.user:
            publisher = self.user.to_public_dict()
            data['user'] = publisher
            data['publisher'] = publisher
        return data

    def __repr__(self):
        return f'<Demand {self.title}>'

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    related_item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=True)
    related_skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), nullable=True)
    related_demand_id = db.Column(db.Integer, db.ForeignKey('demand.id'), nullable=True)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy='dynamic'))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_messages', lazy='dynamic'))

    item = db.relationship('Item', backref=db.backref('messages', lazy='dynamic'))
    skill = db.relationship('Skill', backref=db.backref('messages', lazy='dynamic'))
    demand = db.relationship('Demand', backref=db.backref('messages', lazy='dynamic'))

    def to_dict(self, include_sender=False, include_receiver=False):
        data = {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'content': self.content,
            'related_item_id': self.related_item_id,
            'read_at': self.read_at.isoformat() + 'Z' if self.read_at else None,
            'created_at': self.created_at.isoformat() + 'Z'
        }
        if include_sender and self.sender:
            data['sender'] = {
                'id': self.sender.id,
                'nickname': self.sender.nickname,
                'avatar_url': self.sender.avatar_url
            }
        if include_receiver and self.receiver:
            data['receiver'] = {
                'id': self.receiver.id,
                'nickname': self.receiver.nickname,
                'avatar_url': self.receiver.avatar_url
            }
        return data

    def __repr__(self):
        return f'<Message {self.id}>'

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), nullable=True)
    demand_id = db.Column(db.Integer, db.ForeignKey('demand.id'), nullable=True)
    transaction_type = db.Column(db.String(64), nullable=False, index=True)  # e.g., 'skill_service', 'item_rental', 'item_purchase', 'item_exchange'
    status = db.Column(db.String(64), nullable=False, default='pending_approval', index=True) # e.g., 'pending_approval', 'accepted', 'rejected', 'in_progress', 'completed', 'cancelled_by_requester', 'cancelled_by_provider'
    agreed_terms = db.Column(db.Text, nullable=True) # JSON or Text
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    requester = db.relationship('User', foreign_keys=[requester_id], backref=db.backref('requested_transactions', lazy='dynamic'))
    provider = db.relationship('User', foreign_keys=[provider_id], backref=db.backref('provided_transactions', lazy='dynamic'))
    item = db.relationship('Item', backref=db.backref('transactions', lazy='dynamic'))
    skill = db.relationship('Skill', backref=db.backref('transactions', lazy='dynamic'))
    demand = db.relationship('Demand', backref=db.backref('transactions', lazy='dynamic'))

    def to_dict(self):
        data = {
            'id': self.id,
            'requester_id': self.requester_id,
            'provider_id': self.provider_id,
            'initiator_id': self.requester_id,
            'acceptor_id': self.provider_id,
            'item_id': self.item_id,
            'transaction_type': self.transaction_type,
            'status': self.status,
            'agreed_terms': self.agreed_terms,
            'created_at': self.created_at.isoformat() + 'Z',
            'updated_at': self.updated_at.isoformat() + 'Z'
        }
        data['requester'] = self.requester.to_public_dict() if self.requester else None
        data['provider'] = self.provider.to_public_dict() if self.provider else None
        data['initiator'] = data['requester']
        data['acceptor'] = data['provider']
        data['item'] = self.item.to_dict() if self.item else None
        return data

    def __repr__(self):
        return f'<Transaction {self.id}>'

class Review(db.Model):
    __table_args__ = (
        db.UniqueConstraint(
            'transaction_id',
            'reviewer_id',
            name='uq_review_transaction_reviewer',
        ),
        db.CheckConstraint(
            'rating >= 1 AND rating <= 5',
            name='ck_review_rating',
        ),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False, index=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    reviewee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False) # 1-5
    comment = db.Column(db.Text, nullable=True)
    reply = db.Column(db.Text, nullable=True)
    replied_at = db.Column(db.DateTime, nullable=True)
    review_type = db.Column(db.String(32), nullable=False) # e.g. 'to_provider', 'to_requester'
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    transaction = db.relationship('Transaction', backref=db.backref('reviews', lazy='dynamic'))
    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref=db.backref('given_reviews', lazy='dynamic'))
    reviewee = db.relationship('User', foreign_keys=[reviewee_id], backref=db.backref('received_reviews', lazy='dynamic'))

    def to_dict(self):
        transaction_type = None
        transaction_title = None
        if self.transaction:
            if self.transaction.item:
                transaction_type = 'item'
                transaction_title = self.transaction.item.title
        data = {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'reviewer_id': self.reviewer_id,
            'reviewee_id': self.reviewee_id,
            'rating': self.rating,
            'comment': self.comment,
            'content': self.comment,
            'transaction_type': transaction_type,
            'transaction_title': transaction_title,
            'replied': bool(self.reply),
            'reply': {
                'content': self.reply,
                'created_at': self.replied_at.isoformat() + 'Z' if self.replied_at else None,
            } if self.reply else None,
            'replied_at': self.replied_at.isoformat() + 'Z' if self.replied_at else None,
            'review_type': self.review_type,
            'created_at': self.created_at.isoformat() + 'Z'
        }
        data['reviewer'] = self.reviewer.to_public_dict() if self.reviewer else None
        data['reviewee'] = self.reviewee.to_public_dict() if self.reviewee else None
        return data


    def __repr__(self):
        return f'<Review {self.id} for Transaction {self.transaction_id}>'
