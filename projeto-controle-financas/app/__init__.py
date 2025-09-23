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
    
    # A importação do blueprint deve vir aqui para evitar a importação circular.
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app

# O user_loader deve ser definido após login_manager. Isso também
# é um bom lugar para importar o modelo de usuário para evitar o erro de
# importação circular com o banco de dados.
@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))
