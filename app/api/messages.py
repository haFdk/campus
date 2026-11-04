# app/api/messages.py
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Item, Message, User, utc_now
from app.api import bp as api
from app.api.scope import message_scope
from app.api.utils import current_user_id, pagination_args
from sqlalchemy import or_, and_

@api.route('/messages', methods=['POST'])
@jwt_required()
def send_message():
    data = request.get_json() or {}
    sender_id = current_user_id()

    receiver_id = data.get('receiver_id')
    content = (data.get('content') or '').strip()
    related_item_id = data.get('related_item_id')
    if data.get('related_skill_id') is not None or data.get('related_demand_id') is not None:
        return jsonify({'message': 'Only item references are supported'}), 400

    try:
        receiver_id = int(receiver_id)
    except (TypeError, ValueError):
        receiver_id = None

    if not receiver_id or not content:
        return jsonify({'message': 'Receiver ID and content are required'}), 400

    if receiver_id == sender_id:
        return jsonify({'message': 'Cannot send message to yourself'}), 400

    receiver = db.session.get(User, receiver_id)
    if not receiver:
        return jsonify({'message': 'Receiver not found'}), 404

    if related_item_id and not db.session.get(Item, related_item_id):
        return jsonify({'message': 'Related item not found'}), 404

    message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content,
        related_item_id=related_item_id,
    )
    db.session.add(message)
    db.session.commit()

    return jsonify({'message': 'Message sent successfully', 'chat_message': message.to_dict(include_sender=True, include_receiver=True)}), 201

@api.route('/messages/conversation/<int:other_user_id>', methods=['GET'])
@jwt_required()
def get_conversation(other_user_id):
    user_id = current_user_id()
    page, per_page = pagination_args(default=30, maximum=100)
    other_user = db.session.get(User, other_user_id)
    if not other_user:
        return jsonify({'message': 'User not found'}), 404

    # Mark messages as read
    Message.query.filter(message_scope(), 
        Message.sender_id == other_user_id,
        Message.receiver_id == user_id,
        Message.read_at.is_(None)
    ).update({'read_at': utc_now()})
    db.session.commit()

    messages_query = Message.query.filter(message_scope(), 
        or_(
            and_(Message.sender_id == user_id, Message.receiver_id == other_user_id),
            and_(Message.sender_id == other_user_id, Message.receiver_id == user_id)
        )
    ).order_by(Message.created_at.desc())

    paginated_messages = messages_query.paginate(page=page, per_page=per_page, error_out=False)
    messages = [msg.to_dict(include_sender=True, include_receiver=True) for msg in paginated_messages.items]

    return jsonify({
        'items': messages,
        'meta': {
            'page': paginated_messages.page,
            'per_page': paginated_messages.per_page,
            'total_pages': paginated_messages.pages,
            'total_items': paginated_messages.total
        }
    })

@api.route('/messages/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    user_id = current_user_id()

    # Subquery to get the latest message_id for each conversation partner
    latest_message_subquery = db.session.query(
        db.func.max(Message.id).label('latest_id')
    ).filter(
        message_scope(),
        or_(Message.sender_id == user_id, Message.receiver_id == user_id)
    ).group_by(
        db.case(
            (Message.sender_id == user_id, Message.receiver_id),
            else_=Message.sender_id
        )
    ).subquery()

    # Query to get the actual latest messages based on the subquery
    latest_messages = db.session.query(Message).join(
        latest_message_subquery,
        Message.id == latest_message_subquery.c.latest_id
    ).order_by(Message.created_at.desc()).all()

    conversations = []
    for message in latest_messages:
        other_user_id = message.receiver_id if message.sender_id == user_id else message.sender_id
        other_user = db.session.get(User, other_user_id)
        if not other_user:
            continue

        unread_count = db.session.query(db.func.count(Message.id)).filter(
            Message.sender_id == other_user_id,
            Message.receiver_id == user_id,
            Message.read_at.is_(None)
        ).filter(message_scope()).scalar()

        conversations.append({
            'id': other_user_id,
            'other_user': other_user.to_public_dict(),
            'last_message_text': message.content,
            'last_message_time': message.created_at.isoformat() + 'Z',
            'last_message': {
                'content_excerpt': (message.content[:50] + '...') if len(message.content) > 50 else message.content,
                'created_at': message.created_at.isoformat() + 'Z'
            },
            'unread_count': unread_count
        })

    return jsonify({'conversations': conversations})

@api.route('/messages/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    user_id = current_user_id()

    unread_count = db.session.query(db.func.count(Message.id)).filter(
        Message.receiver_id == user_id,
        Message.read_at.is_(None)
    ).filter(message_scope()).scalar()

    return jsonify({'unread_count': unread_count})

@api.route('/messages/conversation/<int:other_user_id>/mark_read', methods=['POST'])
@jwt_required()
def mark_conversation_as_read(other_user_id):
    user_id = current_user_id()

    messages_to_update = Message.query.filter(message_scope(), 
        Message.sender_id == other_user_id,
        Message.receiver_id == user_id,
        Message.read_at.is_(None)
    )

    updated_count = messages_to_update.update({'read_at': utc_now()}, synchronize_session=False)
    db.session.commit()

    if updated_count > 0:
        return jsonify({'message': f'{updated_count} messages marked as read'}), 200
    else:
        return jsonify({'message': 'No new messages to mark as read'}), 200
