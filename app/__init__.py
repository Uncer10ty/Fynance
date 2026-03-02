import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Ensure required directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')), ''), exist_ok=True)
    
    # Ensure data directory exists
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)

    db.init_app(app)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.accounts import accounts_bp
    from app.routes.transactions import transactions_bp
    from app.routes.categories import categories_bp
    from app.routes.imports import imports_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(accounts_bp, url_prefix='/accounts')
    app.register_blueprint(transactions_bp, url_prefix='/transactions')
    app.register_blueprint(categories_bp, url_prefix='/categories')
    app.register_blueprint(imports_bp, url_prefix='/imports')

    return app
