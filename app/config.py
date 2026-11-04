# app/config.py
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '..', '.env')) # 加载 .env 文件，如果存在

class Config:
    CLASSIFICATION_ENABLED = os.environ.get('CLASSIFICATION_ENABLED', 'true').lower() == 'true'
    CLASSIFICATION_MODEL_PATH = os.environ.get('CLASSIFICATION_MODEL_PATH') or os.path.join(basedir, '..', 'models', 'mdeberta')
    CLASSIFICATION_THREADS = int(os.environ.get('CLASSIFICATION_THREADS', '2'))
    CLASSIFICATION_TEMPLATE = '这段文字描述的是{label}。'
    CLASSIFICATION_BATCH_SIZE = 8
    CLASSIFICATION_HYBRID_MIN_SUPPORT = 0.55
    CLASSIFICATION_MIN_SCORE = float(os.environ.get('CLASSIFICATION_MIN_SCORE', '0.45'))
    CLASSIFICATION_MIN_SUPPORT = float(os.environ.get('CLASSIFICATION_MIN_SUPPORT', '0.70'))
    CLASSIFICATION_MIN_MARGIN = float(os.environ.get('CLASSIFICATION_MIN_MARGIN', '0.25'))
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-only-secret-change-me'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-only-jwt-secret-change-me'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 86400))
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get(
            'CORS_ORIGINS',
            'http://localhost:3000,http://127.0.0.1:3000',
        ).split(',')
        if origin.strip()
    ]
