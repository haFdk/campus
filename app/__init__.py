# app/__init__.py
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object('app.config.Config')
    if config_overrides:
        app.config.update(config_overrides)

    from app.services.classification import Classifier
    app.extensions['item_classifier'] = Classifier(app.config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
    )

    # JWT错误处理
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 422

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        app.logger.info("Invalid token: %s", error)
        return jsonify({'error': 'Invalid token'}), 422

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': 'Authorization token is required'}), 422

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify({'error': 'Method not allowed'}), 405

    return app
