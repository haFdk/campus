from flask import jsonify, request
from flask_jwt_extended import jwt_required

from app import db
from app.api import bp
from app.api.scope import item_transactions, item_reviews
from app.api.errors import bad_request, error_response
from app.api.utils import current_user_id, pagination_args
from app.models import Item, Review, Transaction, User, utc_now


def paginated_reviews(query):
    page, per_page = pagination_args(default=10, maximum=100)
    pagination = (
        query.order_by(Review.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return jsonify({
        'items': [item.to_dict() for item in pagination.items],
        'reviews': [item.to_dict() for item in pagination.items],
        'total': pagination.total,
        'meta': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total_pages': pagination.pages,
            'total_items': pagination.total,
        },
    }), 200


@bp.route('/transactions/<int:transaction_id>/reviews', methods=['POST'])
@jwt_required()
def submit_review(transaction_id):
    reviewer_id = current_user_id()
    transaction = item_transactions().filter_by(id=transaction_id).first_or_404()
    data = request.get_json() or {}
    if transaction.status != 'completed':
        return bad_request('Reviews can only be submitted for completed transactions.')

    rating = data.get('rating')
    if isinstance(rating, float) and rating.is_integer():
        rating = int(rating)
    if not isinstance(rating, int) or not 1 <= rating <= 5:
        return bad_request('Rating must be an integer between 1 and 5.')

    if reviewer_id == transaction.requester_id:
        reviewee_id = transaction.provider_id
        review_type = 'to_provider'
    elif reviewer_id == transaction.provider_id:
        reviewee_id = transaction.requester_id
        review_type = 'to_requester'
    else:
        return error_response(403, 'You are not part of this transaction.')

    requested_type = data.get('review_type')
    if requested_type and requested_type != review_type:
        return bad_request('review_type does not match your transaction role.')
    if item_reviews().filter_by(
        transaction_id=transaction_id,
        reviewer_id=reviewer_id,
    ).first():
        return error_response(409, 'You have already reviewed this transaction.')

    review = Review(
        transaction_id=transaction_id,
        reviewer_id=reviewer_id,
        reviewee_id=reviewee_id,
        rating=rating,
        comment=(data.get('comment') or data.get('content') or '').strip(),
        review_type=review_type,
    )
    db.session.add(review)
    db.session.commit()
    return jsonify({'message': 'Review submitted.', 'review': review.to_dict()}), 201


@bp.route('/reviews/received', methods=['GET'])
@jwt_required()
def get_received_reviews():
    return paginated_reviews(item_reviews().filter_by(reviewee_id=current_user_id()))


@bp.route('/reviews/given', methods=['GET'])
@jwt_required()
def get_given_reviews():
    return paginated_reviews(item_reviews().filter_by(reviewer_id=current_user_id()))


@bp.route('/reviews/<int:review_id>', methods=['GET'])
def get_review(review_id):
    return jsonify({'review': item_reviews().filter_by(id=review_id).first_or_404().to_dict()}), 200


@bp.route('/reviews/<int:review_id>', methods=['PUT'])
@jwt_required()
def update_review(review_id):
    review = item_reviews().filter_by(id=review_id).first_or_404()
    if review.reviewer_id != current_user_id():
        return error_response(403, 'You can only edit your own review.')
    data = request.get_json() or {}
    rating = data.get('rating', review.rating)
    if not isinstance(rating, int) or not 1 <= rating <= 5:
        return bad_request('Rating must be an integer between 1 and 5.')
    review.rating = rating
    review.comment = (
        data.get('comment', data.get('content', review.comment)) or ''
    ).strip()
    db.session.commit()
    return jsonify({'review': review.to_dict()}), 200


@bp.route('/reviews/<int:review_id>', methods=['DELETE'])
@jwt_required()
def delete_review(review_id):
    review = item_reviews().filter_by(id=review_id).first_or_404()
    if review.reviewer_id != current_user_id():
        return error_response(403, 'You can only delete your own review.')
    db.session.delete(review)
    db.session.commit()
    return jsonify({'message': 'Review deleted successfully'}), 200


@bp.route('/reviews/<int:review_id>/reply', methods=['POST'])
@jwt_required()
def reply_to_review(review_id):
    review = item_reviews().filter_by(id=review_id).first_or_404()
    if review.reviewee_id != current_user_id():
        return error_response(403, 'Only the reviewed user can reply.')
    data = request.get_json() or {}
    reply = (data.get('reply') or data.get('content') or '').strip()
    if not reply:
        return bad_request('Reply cannot be empty.')
    review.reply = reply
    review.replied_at = utc_now()
    db.session.commit()
    return jsonify({'review': review.to_dict()}), 200


@bp.route('/users/<int:user_id>/reviews', methods=['GET'])
def get_user_reviews(user_id):
    User.query.get_or_404(user_id)
    return paginated_reviews(item_reviews().filter_by(reviewee_id=user_id))


@bp.route('/items/<int:item_id>/reviews', methods=['GET'])
def get_item_reviews(item_id):
    item = Item.query.get_or_404(item_id)
    return paginated_reviews(
        item_reviews().join(Transaction).filter(
            Transaction.item_id == item_id,
            Review.reviewee_id == item.user_id,
        )
    )
