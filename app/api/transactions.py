import json
from flask import jsonify, request
from flask_jwt_extended import jwt_required

from app import db
from app.api import bp
from app.api.errors import bad_request, error_response
from app.api.utils import current_user_id, pagination_args
from app.models import Item, Message, Transaction, utc_now
from app.api.scope import item_transactions


def transaction_view(transaction, viewer_id=None):
    data = transaction.to_dict()
    if transaction.item:
        details = {}
        try:
            details = json.loads(transaction.agreed_terms or '{}')
        except json.JSONDecodeError:
            pass
        if not isinstance(details, dict):
            details = {}
        data.update({
            'type': 'item',
            'title': transaction.item.title,
            'description': details.get('message') or '物品交换申请',
            'amount': transaction.item.sale_price,
            'offered_item_id': details.get('offered_item_id'),
        })

    else:
        data.update({
            'type': transaction.transaction_type,
            'title': '交易记录',
            'description': transaction.agreed_terms or '',
            'amount': None,
        })
    data['role'] = (
        'initiator' if viewer_id == transaction.requester_id else 'acceptor'
        if viewer_id == transaction.provider_id else None
    )
    data['reviewed'] = any(
        review.reviewer_id == viewer_id for review in transaction.reviews
    ) if viewer_id else False
    data['completed_at'] = (
        transaction.updated_at.isoformat() + 'Z'
        if transaction.status == 'completed' else None
    )
    return data


def notify(transaction, content):
    db.session.add(Message(
        sender_id=current_user_id(),
        receiver_id=transaction.requester_id,
        content=content,
        related_item_id=transaction.item_id,
    ))


@bp.route('/transactions/exchange-requests', methods=['POST'])
@jwt_required()
def create_exchange_request():
    user_id = current_user_id()
    data = request.get_json() or {}
    target = db.session.get(Item, data.get('target_item_id'))
    offered = db.session.get(Item, data.get('offered_item_id'))
    if not target or not offered:
        return bad_request('Target and offered items are required.')
    if target.user_id == user_id:
        return bad_request('You cannot request your own item.')
    if offered.user_id != user_id:
        return error_response(403, 'You can only offer your own item.')
    if target.status != 'available' or offered.status != 'available':
        return bad_request('Both items must be available.')

    details = {
        'offered_item_id': offered.id,
        'message': (data.get('message') or '').strip(),
        'contact_phone': data.get('contact_phone'),
        'contact_wechat': data.get('contact_wechat'),
    }
    transaction = Transaction(
        requester_id=user_id,
        provider_id=target.user_id,
        item_id=target.id,
        transaction_type='item_exchange',
        status='pending_approval',
        agreed_terms=json.dumps(details, ensure_ascii=False),
    )
    db.session.add(transaction)
    db.session.add(Message(
        sender_id=user_id,
        receiver_id=target.user_id,
        content=f"我想用「{offered.title}」交换你的「{target.title}」。",
        related_item_id=target.id,
    ))
    db.session.commit()
    return jsonify({
        'message': 'Exchange request sent.',
        'transaction': transaction_view(transaction, user_id),
    }), 201


@bp.route('/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    user_id = current_user_id()
    page, per_page = pagination_args(default=10)
    query = item_transactions().filter(
        db.or_(Transaction.requester_id == user_id, Transaction.provider_id == user_id)
    )

    role = request.args.get('role')
    if role == 'initiator':
        query = query.filter(Transaction.requester_id == user_id)
    elif role == 'acceptor':
        query = query.filter(Transaction.provider_id == user_id)

    status = request.args.get('status')
    if status == 'ongoing':
        query = query.filter(Transaction.status.in_(
            ('pending_approval', 'accepted', 'in_progress')
        ))
    elif status == 'cancelled':
        query = query.filter(Transaction.status.in_(
            ('rejected', 'cancelled_by_requester', 'cancelled_by_provider')
        ))
    elif status:
        query = query.filter(Transaction.status == status)

    kind = request.args.get('type')
    if kind and kind != 'item':
        return bad_request('Only item transactions are supported.')

    pagination = (
        query.order_by(Transaction.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return jsonify({
        'transactions': [
            transaction_view(item, user_id) for item in pagination.items
        ],
        'total': pagination.total,
        'meta': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total_pages': pagination.pages,
            'total_items': pagination.total,
        },
    }), 200


@bp.route('/transactions/<int:transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction(transaction_id):
    user_id = current_user_id()
    transaction = item_transactions().filter_by(id=transaction_id).first_or_404()
    if user_id not in (transaction.requester_id, transaction.provider_id):
        return error_response(403, 'You are not part of this transaction.')
    return jsonify({'transaction': transaction_view(transaction, user_id)}), 200


@bp.route('/transactions/<int:transaction_id>/respond', methods=['PUT'])
@jwt_required()
def respond_to_transaction(transaction_id):
    user_id = current_user_id()
    transaction = item_transactions().filter_by(id=transaction_id).first_or_404()
    if transaction.provider_id != user_id:
        return error_response(403, 'Only the provider can respond to this transaction.')
    if transaction.status != 'pending_approval':
        return bad_request(f'This transaction is already {transaction.status}.')

    action = (request.get_json() or {}).get('action')
    if action not in ('accept', 'reject'):
        return bad_request('Action must be accept or reject.')

    transaction.status = 'accepted' if action == 'accept' else 'rejected'
    transaction.updated_at = utc_now()
    notify(transaction, f"你的交易请求已被{'接受' if action == 'accept' else '婉拒'}。")
    db.session.commit()
    return jsonify({
        'message': 'Transaction status updated.',
        'transaction': transaction_view(transaction, user_id),
    }), 200


@bp.route('/transactions/<int:transaction_id>/complete', methods=['PUT'])
@jwt_required()
def complete_transaction(transaction_id):
    user_id = current_user_id()
    transaction = item_transactions().filter_by(id=transaction_id).first_or_404()
    if user_id not in (transaction.requester_id, transaction.provider_id):
        return error_response(403, 'You are not part of this transaction.')
    if transaction.status not in ('accepted', 'in_progress'):
        return bad_request('Only accepted transactions can be completed.')

    offered = None
    if transaction.transaction_type == 'item_exchange':
        try:
            terms = json.loads(transaction.agreed_terms or '{}')
            offered_id = terms.get('offered_item_id') if isinstance(terms, dict) else None
        except json.JSONDecodeError:
            offered_id = None
        if offered_id:
            offered = db.session.get(Item, offered_id)
            if not offered or offered.user_id != transaction.requester_id or offered.status != 'available':
                return bad_request('The offered item is no longer available.')
    if transaction.item.status != 'available':
        return bad_request('The target item is no longer available.')
    if offered:
        offered.status = 'exchanged'
    transaction.status = 'completed'
    transaction.updated_at = utc_now()
    if transaction.item:
        transaction.item.status = (
            'exchanged' if transaction.transaction_type == 'item_exchange' else
            'available' if transaction.transaction_type == 'item_rental' else 'sold'
        )
    db.session.commit()
    return jsonify({'transaction': transaction_view(transaction, user_id)}), 200


@bp.route('/transactions/<int:transaction_id>/cancel', methods=['PUT'])
@jwt_required()
def cancel_transaction(transaction_id):
    user_id = current_user_id()
    transaction = item_transactions().filter_by(id=transaction_id).first_or_404()
    if user_id not in (transaction.requester_id, transaction.provider_id):
        return error_response(403, 'You are not part of this transaction.')
    if transaction.status in ('completed', 'rejected'):
        return bad_request('This transaction can no longer be cancelled.')

    transaction.status = (
        'cancelled_by_requester'
        if user_id == transaction.requester_id
        else 'cancelled_by_provider'
    )
    db.session.commit()
    return jsonify({'transaction': transaction_view(transaction, user_id)}), 200


@bp.route('/users/<int:user_id>/transactions', methods=['GET'])
@jwt_required()
def get_user_transactions(user_id):
    if user_id != current_user_id():
        return error_response(403, 'You can only view your own transactions.')
    return get_transactions()
