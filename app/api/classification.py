from flask import current_app, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.api import bp
from app.models import User
from app.services.classification import ClassificationBusy, ClassificationUnavailable


@bp.route('/items/category-suggestion', methods=['POST'])
@jwt_required()
def suggest_category():
    if db.session.get(User, int(get_jwt_identity())) is None:
        return jsonify(error='账号不存在'), 403
    if request.content_length is not None and request.content_length > 8192:
        return jsonify(error='请求内容过长'), 413
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='请提供商品标题'), 400
    value = data.get('title', '')
    if not isinstance(value, str) or len(value) > 50:
        return jsonify(error='标题格式不正确，或超过 50 字符'), 400
    title = ' '.join(data.get('title', '').split())
    if not title:
        return jsonify(status='uncertain', category=None, candidates=[], source='none', degraded=False,
                       version='hybrid-v1', message='请填写具体商品名称，如：高等数学教材、蓝牙耳机'), 200
    try:
        return jsonify(current_app.extensions['item_classifier'].recommend(title))
    except ClassificationBusy:
        return jsonify(error='智能分类正在处理其他请求，请稍后重试或手动选择'), 429
    except ClassificationUnavailable:
        return jsonify(error='智能分类暂不可用，请手动选择分类'), 503
