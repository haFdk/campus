from flask import jsonify

from app import db
from app.api import bp
from app.models import Item, User
from app.api.scope import item_transactions


@bp.route('/health', methods=['GET'])
def health():
    db.session.execute(db.select(db.literal(1)))
    return jsonify({'status': 'ok', 'service': 'campus-loop-api', 'edition': 'items-only-v1',
                    'capabilities': ['category-suggestion-title-v2', 'category-suggestion-hybrid-v3']}), 200


@bp.route('/stats', methods=['GET'])
def platform_stats():
    return jsonify({
        'users': User.query.count(),
        'items': Item.query.filter_by(status='available').count(),
        'transactions': item_transactions().count(),
        'completed_transactions': item_transactions().filter_by(status='completed').count(),
    }), 200
