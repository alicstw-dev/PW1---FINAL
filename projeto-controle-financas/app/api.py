from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Transaction, Card
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import login_user, logout_user, current_user, login_required

api_bp = Blueprint("api", __name__, url_prefix="/api")

# ---------------- AUTH ---------------- #

@api_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    if not data or "username" not in data or "email" not in data or "password" not in data:
        return jsonify({"error": "Dados incompletos"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Usuário já existe"}), 400

    user = User(username=data["username"], email=data["email"])
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Usuário registrado com sucesso"}), 201


@api_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "Dados incompletos"}), 400

    user = User.query.filter_by(email=data["email"]).first()
    if user and user.check_password(data["password"]):
        login_user(user)
        return jsonify({"message": "Login realizado com sucesso"})
    return jsonify({"error": "Credenciais inválidas"}), 401


@api_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout realizado com sucesso"})


# ---------------- TRANSACTIONS ---------------- #

@api_bp.route("/transactions", methods=["GET"])
@login_required
def get_transactions():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    return jsonify([
        {
            "id": t.id,
            "type": t.type,
            "amount": t.amount,
            "description": t.description,
            "payment_method": t.payment_method,
            "category": t.category,
            "date": t.date.isoformat()
        } for t in transactions
    ])


@api_bp.route("/transactions", methods=["POST"])
@login_required
def add_transaction():
    data = request.json
    t = Transaction(
        type=data["type"],
        amount=data["amount"],
        description=data.get("description"),
        payment_method=data.get("payment_method"),
        category=data.get("category"),
        user_id=current_user.id
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({"message": "Transação adicionada com sucesso"}), 201


@api_bp.route("/transactions/<int:id>", methods=["PUT"])
@login_required
def update_transaction(id):
    t = Transaction.query.get_or_404(id)
    if t.user_id != current_user.id:
        return jsonify({"error": "Não autorizado"}), 403

    data = request.json
    t.type = data.get("type", t.type)
    t.amount = data.get("amount", t.amount)
    t.description = data.get("description", t.description)
    t.payment_method = data.get("payment_method", t.payment_method)
    t.category = data.get("category", t.category)
    db.session.commit()
    return jsonify({"message": "Transação atualizada"})


@api_bp.route("/transactions/<int:id>", methods=["DELETE"])
@login_required
def delete_transaction(id):
    t = Transaction.query.get_or_404(id)
    if t.user_id != current_user.id:
        return jsonify({"error": "Não autorizado"}), 403
    db.session.delete(t)
    db.session.commit()
    return jsonify({"message": "Transação removida"})


# ---------------- CARDS ---------------- #

@api_bp.route("/cards", methods=["GET"])
@login_required
def get_cards():
    cards = Card.query.filter_by(user_id=current_user.id).all()
    return jsonify([{"id": c.id, "name": c.name, "due_day": c.due_day} for c in cards])


@api_bp.route("/cards", methods=["POST"])
@login_required
def add_card():
    data = request.json
    c = Card(
        name=data["name"],
        due_day=data["due_day"],
        user_id=current_user.id
    )
    db.session.add(c)
    db.session.commit()
    return jsonify({"message": "Cartão adicionado com sucesso"}), 201
