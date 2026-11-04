# app/api/__init__.py
from flask import Blueprint

bp = Blueprint('api', __name__)

# Import API resources here to register them with the blueprint
from app.api import auth, items, messages, meta, reviews, transactions, classification
