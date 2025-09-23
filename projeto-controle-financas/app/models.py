from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

# A classe User agora herda de UserMixin para que o Flask-Login possa gerenciar o usuário.
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    transactions = db.relationship('Transaction', backref='author', lazy='dynamic')
    cards = db.relationship('Card', backref='owner', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

    # Método para definir a senha do usuário
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Método para verificar a senha do usuário
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Tabela de transações financeiras
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10), nullable=False) # 'income' ou 'expense'
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    payment_method = db.Column(db.String(50))
    category = db.Column(db.String(50))
    date = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Transaction {self.description}>'

# Tabela para cartões de crédito
class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    due_day = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Card {self.name}>'
