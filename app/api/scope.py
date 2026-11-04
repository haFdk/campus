"""Keep retired records in storage, outside current business queries."""
from app.models import Message, Review, Transaction

def item_scope():
    return (
        Transaction.item_id.isnot(None)
        & Transaction.skill_id.is_(None)
        & Transaction.demand_id.is_(None)
        & Transaction.transaction_type.in_(('item_exchange', 'item_purchase', 'item_rental'))
    )

def item_transactions():
    return Transaction.query.filter(item_scope())

def item_reviews():
    return Review.query.filter(Review.transaction.has(item_scope()))

def message_scope():
    return Message.related_skill_id.is_(None) & Message.related_demand_id.is_(None)
