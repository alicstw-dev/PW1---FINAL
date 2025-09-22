from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# inicializa extensões
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # inicializa banco e migrações
    db.init_app(app)
    migrate.init_app(app, db)

    # Move a importação e o registro do blueprint para cá.
    # Isso garante que db e app já existem quando o routes.py é executado.
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app
