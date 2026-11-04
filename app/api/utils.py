from datetime import datetime

from flask import request
from flask_jwt_extended import get_jwt_identity


def current_user_id():
    """Return the JWT subject as an integer database id."""
    identity = get_jwt_identity()
    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


def pagination_args(default=12, maximum=50):
    """Accept both per_page and the legacy page_size query parameter."""
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = request.args.get(
        "per_page",
        request.args.get("page_size", default, type=int),
        type=int,
    )
    per_page = min(max(per_page or default, 1), maximum)
    return page, per_page


def parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    normalized = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    return parsed.replace(tzinfo=None)
