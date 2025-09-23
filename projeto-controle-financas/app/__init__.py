from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Inicializa extensões fora da função para que possam ser importadas em outros arquivos.
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Inicializa as extensões com o aplicativo.
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    
    # Importa e registra os blueprints
    from .routes import main_bp
    from .api import api_bp
    
    app.register_blueprint(main_bp)   # Rotas Web (HTML)
    app.register_blueprint(api_bp)    # Rotas API (JSON)

    return app

# O user_loader deve ser definido após login_manager.
@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))
