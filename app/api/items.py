# app/api/items.py
from flask import request, jsonify
from app import db
from app.models import Item
from app.api import bp
from app.api.utils import current_user_id, pagination_args
from flask_jwt_extended import jwt_required

@bp.route('/items', methods=['POST'])
@jwt_required()
def create_item():
    user_id = current_user_id()
    data = request.get_json() or {}

    # Required fields
    title = data.get('title')
    description = data.get('description')
    category = data.get('category')
    condition = data.get('condition')
    transaction_type = data.get('transaction_type')

    # Optional fields
    images = data.get('images') # Should be a list of URLs
    exchange_for = data.get('exchange_for')
    rental_price_day = data.get('rental_price_day')
    sale_price = data.get('sale_price')
    location_campus = data.get('location_campus')
    location_building = data.get('location_building')
    status = data.get('status', 'available')

    errors = {}
    if not title:
        errors['title'] = 'Title is required.'
    if description is None:
        description = ''
    elif not isinstance(description, str):
        errors['description'] = 'Description must be text.'
    elif len(description) > 500:
        errors['description'] = 'Description must be 500 characters or fewer.'
    else:
        description = description.strip()
    if not category:
        errors['category'] = 'Category is required.'
    if not condition:
        errors['condition'] = 'Condition is required.'
    if not transaction_type:
        errors['transaction_type'] = 'Transaction type is required.'

    if images is not None and not isinstance(images, list):
        errors['images'] = 'Images should be a list of URLs.'

    # Price validation based on transaction_type
    if transaction_type == '租赁' and (rental_price_day is None or not isinstance(rental_price_day, (int, float)) or rental_price_day <= 0):
        errors['rental_price_day'] = 'Rental price per day must be a positive number for rentals.'
    elif transaction_type == '出售' and (sale_price is None or not isinstance(sale_price, (int, float)) or sale_price <= 0):
        errors['sale_price'] = 'Sale price must be a positive number for sales.'
    elif transaction_type == '交换或出售':
        if (exchange_for is None or exchange_for == '') and (sale_price is None or not isinstance(sale_price, (int, float)) or sale_price <= 0):
             errors['general_price'] = 'Either exchange details or a valid sale price is required for "exchange or sale".'
        elif sale_price is not None and (not isinstance(sale_price, (int,float)) or sale_price <=0):
            errors['sale_price'] = 'Sale price must be a positive number if provided for "exchange or sale".'

    if errors:
        return jsonify({'error': 'Validation error', 'messages': errors}), 400

    item = Item(
        user_id=user_id,
        title=title,
        description=description,
        category=category,
        condition=condition,
        images=images,
        exchange_for=exchange_for if '交换' in transaction_type else None,
        rental_price_day=rental_price_day if transaction_type == '租赁' else None,
        sale_price=sale_price if '出售' in transaction_type else None,
        transaction_type=transaction_type,
        status=status,
        location_campus=location_campus,
        location_building=location_building
    )
    db.session.add(item)
    db.session.commit()

    return jsonify({'message': 'Item created successfully', 'item': item.to_dict(include_user=True)}), 201

@bp.route('/items', methods=['GET'])
def get_items():
    page, per_page = pagination_args()

    # Filters
    category_filter = request.args.get('category')
    user_id_filter = request.args.get('user_id', type=int)
    search_term = request.args.get('search') or request.args.get('keyword')
    condition_filter = request.args.get('condition')
    transaction_type_filter = request.args.get('transaction_type')
    location_campus_filter = request.args.get('location_campus')
    status_filter = request.args.get('status', 'available') # Default to available items

    sort_by = request.args.get('sort_by') or request.args.get('sort')
    exclude_id = request.args.get('exclude', type=int)

    query = Item.query

    if status_filter:
        query = query.filter(Item.status == status_filter)
    if exclude_id:
        query = query.filter(Item.id != exclude_id)
    if category_filter:
        query = query.filter(Item.category == category_filter)
    if user_id_filter:
        query = query.filter(Item.user_id == user_id_filter)
    if search_term:
        query = query.filter(db.or_(Item.title.ilike(f'%{search_term}%'), Item.description.ilike(f'%{search_term}%')))
    if condition_filter:
        query = query.filter(Item.condition == condition_filter)
    if transaction_type_filter:
        query = query.filter(Item.transaction_type == transaction_type_filter)
    if location_campus_filter:
        query = query.filter(Item.location_campus == location_campus_filter)

    if sort_by:
        if sort_by in ('created_at_desc', 'created_at', 'latest', 'views'):
            query = query.order_by(Item.created_at.desc())
        elif sort_by == 'updated_at':
            query = query.order_by(Item.updated_at.desc())
        elif sort_by == 'created_at_asc':
            query = query.order_by(Item.created_at.asc())
        elif sort_by == 'sale_price_asc':
            query = query.filter(Item.sale_price.isnot(None)).order_by(Item.sale_price.asc())
        elif sort_by == 'sale_price_desc':
            query = query.filter(Item.sale_price.isnot(None)).order_by(Item.sale_price.desc())
        elif sort_by == 'rental_price_day_asc':
            query = query.filter(Item.rental_price_day.isnot(None)).order_by(Item.rental_price_day.asc())
        elif sort_by == 'rental_price_day_desc':
            query = query.filter(Item.rental_price_day.isnot(None)).order_by(Item.rental_price_day.desc())
    else:
        query = query.order_by(Item.created_at.desc()) # Default sort

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = pagination.items

    return jsonify({
        'items': [item.to_dict(include_user=True) for item in items],
        'total': pagination.total,
        'meta': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total_pages': pagination.pages,
            'total_items': pagination.total
        }
    }), 200

@bp.route('/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    item = Item.query.get_or_404(item_id)
    return jsonify({'item': item.to_dict(include_user=True)}), 200

@bp.route('/items/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    user_id = current_user_id()
    item = Item.query.get_or_404(item_id)

    if item.user_id != user_id:
        return jsonify({'error': 'Forbidden. You can only update your own items.'}), 403

    data = request.get_json() or {}
    errors = {}

    # Update fields, similar logic to create_item for validation
    if 'title' in data:
        if not data['title']:
            errors['title'] = 'Title cannot be empty.'
        else:
            item.title = data['title']
    if 'description' in data:
        value = data['description']
        if value is not None and not isinstance(value, str):
            errors['description'] = 'Description must be text.'
        elif isinstance(value, str) and len(value) > 500:
            errors['description'] = 'Description must be 500 characters or fewer.'
        else:
            item.description = value.strip() if value is not None else ''
    if 'category' in data:
        if not data['category']:
            errors['category'] = 'Category cannot be empty.'
        else:
            item.category = data['category']
    if 'condition' in data:
        if not data['condition']:
            errors['condition'] = 'Condition cannot be empty.'
        else:
            item.condition = data['condition']
    if 'images' in data:
        if data['images'] is not None and not isinstance(data['images'], list):
            errors['images'] = 'Images should be a list of URLs.'
        else:
            item.images = data['images']

    # Handle transaction_type and related price fields carefully
    if 'transaction_type' in data:
        if not data['transaction_type']:
            errors['transaction_type'] = 'Transaction type cannot be empty.'
        else:
            item.transaction_type = data['transaction_type']
            # Reset prices if type changes to something not requiring them
            if item.transaction_type != '租赁': item.rental_price_day = None
            if '出售' not in item.transaction_type: item.sale_price = None
            if '交换' not in item.transaction_type: item.exchange_for = None

    if 'exchange_for' in data:
        item.exchange_for = data['exchange_for']

    if 'rental_price_day' in data:
        if item.transaction_type == '租赁':
            if data['rental_price_day'] is None or not isinstance(data['rental_price_day'], (int, float)) or data['rental_price_day'] <= 0:
                errors['rental_price_day'] = 'Rental price per day must be a positive number for rentals.'
            else:
                item.rental_price_day = data['rental_price_day']
        else:
            item.rental_price_day = None # Clear if not applicable

    if 'sale_price' in data:
        if '出售' in item.transaction_type:
            if data['sale_price'] is None or not isinstance(data['sale_price'], (int, float)) or data['sale_price'] <= 0:
                errors['sale_price'] = 'Sale price must be a positive number for sales.'
            else:
                item.sale_price = data['sale_price']
        else:
            item.sale_price = None # Clear if not applicable

    # Validation for '交换或出售' after potential updates
    if item.transaction_type == '交换或出售':
        if (item.exchange_for is None or item.exchange_for == '') and (item.sale_price is None or not isinstance(item.sale_price, (int, float)) or item.sale_price <= 0):
             errors['general_price'] = 'Either exchange details or a valid sale price is required for "exchange or sale".'

    if 'location_campus' in data:
        item.location_campus = data['location_campus']
    if 'location_building' in data:
        item.location_building = data['location_building']
    if 'status' in data:
        item.status = data['status']

    if errors:
        return jsonify({'error': 'Validation error', 'messages': errors}), 400

    db.session.commit()
    return jsonify({'message': 'Item updated successfully', 'item': item.to_dict(include_user=True)}), 200

@bp.route('/items/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    user_id = current_user_id()
    item = Item.query.get_or_404(item_id)

    if item.user_id != user_id:
        return jsonify({'error': 'Forbidden. You can only delete your own items.'}), 403

    if item.transactions.count() or item.messages.count():
        item.status = 'unavailable'
        db.session.commit()
        return jsonify({
            'message': 'Item archived because it has transaction history',
            'item': item.to_dict(include_user=True),
        }), 200

    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Item deleted successfully'}), 200


@bp.route('/users/<int:user_id>/items', methods=['GET'])
def get_user_items(user_id):
    page, per_page = pagination_args()
    query = Item.query.filter_by(user_id=user_id)
    if request.args.get('status'):
        query = query.filter_by(status=request.args['status'])
    pagination = (
        query.order_by(Item.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return jsonify({
        'items': [item.to_dict(include_user=True) for item in pagination.items],
        'total': pagination.total,
    }), 200


@bp.route('/items/mine', methods=['GET'])
@jwt_required()
def get_my_items():
    page, per_page = pagination_args()
    query = Item.query.filter_by(user_id=current_user_id())
    for field in ('category', 'condition'):
        if request.args.get(field):
            query = query.filter(getattr(Item, field) == request.args[field])
    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(db.or_(Item.title.ilike(f'%{search}%'), Item.description.ilike(f'%{search}%')))
    if request.args.get('status'):
        query = query.filter_by(status=request.args['status'])
    pagination = (
        query.order_by(Item.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return jsonify({
        'items': [item.to_dict(include_user=True) for item in pagination.items],
        'total': pagination.total,
    }), 200
