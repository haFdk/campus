# app/api/auth.py
from flask import request, jsonify
from app import db, jwt
from app.models import Item, Transaction, User
from app.api import bp
from app.api.scope import item_transactions
from app.api.utils import current_user_id
from flask_jwt_extended import create_access_token, jwt_required, get_jwt
import re

# 简单的邮箱格式校验
def is_valid_email(email):
    if re.fullmatch(r'[^@]+@[^@]+\.[^@]+', email):
        return True
    return False

@bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password')
    username = (data.get('username') or data.get('nickname') or '').strip()

    errors = {}
    if not email:
        errors['email'] = 'Email is required.'
    elif not is_valid_email(email):
        errors['email'] = 'Invalid email format.'
    if not password:
        errors['password'] = 'Password is required.'
    elif len(password) < 6:
        errors['password'] = 'Password must contain at least 6 characters.'
    if not username:
        errors['username'] = 'Username is required.'

    if errors:
        return jsonify({'error': 'Validation error', 'messages': errors}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 409
    if User.query.filter_by(nickname=username).first():  # 数据库中仍使用nickname字段
        return jsonify({'error': 'Username already exists'}), 409

    user = User(email=email, nickname=username)  # 将username存储到nickname字段
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully', 'user': user.to_dict()}), 201

@bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    # 支持用户名或邮箱登录
    if is_valid_email(username):
        user = User.query.filter_by(email=username.lower()).first()
    else:
        user = User.query.filter_by(nickname=username).first()

    if user is None or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({'message': 'Login successful', 'access_token': access_token, 'user': user.to_dict()}), 200

@bp.route('/auth/me', methods=['GET'])
@jwt_required()
def get_me():
    user = db.session.get(User, current_user_id())

    if user is None:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(user.to_dict()), 200

@bp.route('/auth/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user = db.session.get(User, current_user_id())
    if user is None:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict()), 200


@bp.route('/users/<int:user_id>', methods=['GET'])
def get_public_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    return jsonify(user.to_public_dict()), 200


@bp.route('/auth/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user = db.session.get(User, current_user_id())

    if user is None:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json() or {}

    nickname = data.get('username', data.get('nickname'))
    if nickname is not None:
        nickname = nickname.strip()
        if not nickname:
            return jsonify({'message': 'Username cannot be empty'}), 400
        duplicate = User.query.filter(User.nickname == nickname, User.id != user.id).first()
        if duplicate:
            return jsonify({'message': 'Username already exists'}), 409
        user.nickname = nickname
    if 'avatar_url' in data:
        user.avatar_url = data['avatar_url']
    if 'major' in data:
        user.major = data['major']
    if 'grade' in data:
        user.grade = data['grade']

    db.session.commit()
    return jsonify({'message': 'Profile updated successfully', 'user': user.to_dict()}), 200


@bp.route('/auth/change-password', methods=['PUT'])
@jwt_required()
def change_password():
    user = db.session.get(User, current_user_id())
    data = request.get_json() or {}
    current_password = data.get('current_password') or data.get('old_password')
    new_password = data.get('new_password')

    if not current_password or not user or not user.check_password(current_password):
        return jsonify({'message': 'Current password is incorrect'}), 400
    if not new_password or len(new_password) < 6:
        return jsonify({'message': 'New password must contain at least 6 characters'}), 400

    user.set_password(new_password)
    db.session.commit()
    return jsonify({'message': 'Password updated successfully'}), 200


@bp.route('/auth/stats', methods=['GET'])
@jwt_required()
def get_user_stats():
    user_id = current_user_id()
    transaction_count = item_transactions().filter(
        db.or_(
            Transaction.requester_id == user_id,
            Transaction.provider_id == user_id,
        )
    ).count()
    return jsonify({
        'items_count': Item.query.filter_by(user_id=user_id).count(),
        'transactions_count': transaction_count,
    }), 200

# 存储已撤销的Token JTI (JWT ID)
# 在实际生产中，您应该使用更持久的存储，如Redis或数据库表
revoked_tokens = set()

@jwt.token_in_blocklist_loader
def check_if_token_in_blocklist(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    return jti in revoked_tokens

@bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    revoked_tokens.add(jti)
    return jsonify({'message': 'Logout successful. Token has been invalidated.'}), 200

# 如果暂时不实现黑名单，可以使用下面的占位API
# @bp.route('/auth/logout', methods=['POST'])
# @jwt_required()
# def logout_placeholder():
#     return jsonify({'message': 'Logout successful. Please clear your token on the client side.'}), 200
