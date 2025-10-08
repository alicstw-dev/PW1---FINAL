from flask import render_template, redirect, url_for, request, Blueprint, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Transaction, Card
from sqlalchemy import func, extract
from datetime import datetime
from calendar import monthrange
from collections import defaultdict

main_bp = Blueprint('main', __name__)

@main_bp.app_template_filter('format_date')
def format_date_filter(value):
    """Filtro para formatar um objeto de data ou string de data."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime('%d/%m/%Y')
    return datetime.fromisoformat(value).strftime('%d/%m/%Y')

# Rota de Login e principal
@main_bp.route('/', methods=['GET', 'POST'])
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            flash('Por favor, preencha todos os campos.', 'danger')
            return redirect(url_for('main.login'))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')

    return render_template('login.html')

# Página de Registro
@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Usuário ou e-mail já cadastrados.', 'warning')
            return redirect(url_for('main.register'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Cadastro realizado com sucesso! Faça login.', 'success')
        return redirect(url_for('main.login'))

    return render_template('register.html')

# Dashboard (só acessível logado)
@main_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    user_id = current_user.id
    
    try:
        selected_month = int(request.args.get('month', datetime.now().month))
        selected_year = int(request.args.get('year', datetime.now().year))
    except (ValueError, TypeError):
        selected_month = datetime.now().month
        selected_year = datetime.now().year
    
    transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        extract('month', Transaction.date) == selected_month,
        extract('year', Transaction.date) == selected_year
    ).order_by(Transaction.date.desc()).all()

    total_income = sum(t.amount for t in transactions if t.type == 'income')
    total_expense = sum(t.amount for t in transactions if t.type == 'expense')
    balance = total_income - total_expense

    years = sorted(list(set(t.date.year for t in Transaction.query.filter_by(user_id=user_id).all())))
    if not years:
        years = [datetime.now().year]

    month_names = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

    credit_card_bill = sum(t.amount for t in transactions if t.payment_method == 'Cartao de Credito' and t.type == 'expense')
    
    invoices = []

    return render_template(
        'dashboard.html', 
        active_page='dashboard',
        balance=balance,
        total_income=total_income,
        total_expense=total_expense,
        transactions=transactions,
        credit_card_bill=credit_card_bill,
        invoices=invoices,
        selected_month=selected_month,
        selected_year=selected_year,
        month_names=month_names,
        years=years
    )

# Adicionar Transação, Renda e Cartão (Rota Unificada)
@main_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    categories = ['Alimentação', 'Transporte', 'Moradia', 'Saúde', 'Lazer', 'Educação', 'Salário', 'Outros']
    cards = Card.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_transaction':
            type_ = request.form.get('type')
            amount = request.form.get('amount')
            description = request.form.get('description', '')
            payment_method = request.form.get('payment_method')
            category = request.form.get('category')
            
            if not all([type_, amount, payment_method, category]):
                flash('Por favor, preencha todos os campos obrigatórios da transação.', 'danger')
                return redirect(url_for('main.add'))
                
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                flash('O valor da transação deve ser um número válido.', 'danger')
                return redirect(url_for('main.add'))

            new_transaction = Transaction(
                type=type_,
                amount=amount,
                description=description,
                payment_method=payment_method,
                category=category,
                user_id=current_user.id
            )
            db.session.add(new_transaction)
            db.session.commit()
            flash('Transação adicionada com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))

        elif action == 'add_income':
            income_value = request.form.get('income_value')
            if not income_value:
                flash('Por favor, insira um valor para a renda.', 'danger')
                return redirect(url_for('main.add'))
            
            try:
                amount = float(income_value)
            except (ValueError, TypeError):
                flash('O valor da renda deve ser um número válido.', 'danger')
                return redirect(url_for('main.add'))

            new_income_transaction = Transaction(
                type='income',
                amount=amount,
                description='Renda Fixa',
                payment_method='Transferencia',
                category='Salario',
                user_id=current_user.id
            )
            db.session.add(new_income_transaction)
            db.session.commit()
            flash('Renda fixa adicionada com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))

        elif action == 'add_card':
            card_name = request.form.get('card_name')
            card_due_day = request.form.get('card_due_day')
            if not card_name or not card_due_day:
                flash('Por favor, preencha todos os campos do cartão.', 'danger')
                return redirect(url_for('main.add'))
            
            try:
                due_day = int(card_due_day)
                if not 1 <= due_day <= 31:
                    raise ValueError("Dia de fechamento inválido.")
            except (ValueError, TypeError):
                flash('O dia de fechamento do cartão deve ser um número entre 1 e 31.', 'danger')
                return redirect(url_for('main.add'))
            
            new_card = Card(
                name=card_name,
                due_day=due_day,
                user_id=current_user.id
            )
            db.session.add(new_card)
            db.session.commit()
            flash('Cartão adicionado com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))
    
    return render_template('add_transaction.html', active_page='add', categories=categories, cards=cards)

# Relatórios
@main_bp.route('/reports')
@login_required
def reports():
    user_id = current_user.id

    try:
        current_year = int(request.args.get('year', datetime.now().year))
        current_month = int(request.args.get('month', datetime.now().month))
    except (ValueError, TypeError):
        current_year = datetime.now().year
        current_month = datetime.now().month
        flash('Filtro de data inválido. Exibindo dados do mês atual.', 'warning')

    start_date = datetime(current_year, current_month, 1)
    end_date = datetime(current_year, current_month, monthrange(current_year, current_month)[1], 23, 59, 59)

    transactions = Transaction.query.filter_by(user_id=user_id) \
                                   .filter(Transaction.date.between(start_date, end_date)) \
                                   .order_by(Transaction.date.desc()) \
                                   .all()
    
    expenses_by_category = defaultdict(float)
    for transaction in transactions:
        if transaction.type == 'expense':
            expenses_by_category[transaction.category] += transaction.amount
    
    expense_labels = list(expenses_by_category.keys())
    expense_data = list(expenses_by_category.values())

    trend_income = defaultdict(float)
    trend_expense = defaultdict(float)
    
    # Gerar todas as datas do mês para o gráfico
    num_days = monthrange(current_year, current_month)[1]
    trend_labels = [f"{day}/{current_month}" for day in range(1, num_days + 1)]
    trend_income_data = [0] * num_days
    trend_expense_data = [0] * num_days

    for transaction in transactions:
        day = transaction.date.day
        if transaction.type == 'income':
            trend_income_data[day - 1] += transaction.amount
        else:
            trend_expense_data[day - 1] += transaction.amount
    
    transactions_data = [{
        'id': t.id,
        'type': t.type,
        'amount': t.amount,
        'description': t.description,
        'payment_method': t.payment_method,
        'category': t.category,
        'date': t.date.isoformat() 
    } for t in transactions]

    cards = Card.query.filter_by(user_id=user_id).all()

    total_income = sum(t.amount for t in transactions if t.type == 'income')
    total_expense = sum(t.amount for t in transactions if t.type == 'expense')
    balance = total_income - total_expense

    month_names = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    all_categories = sorted(list(set(t.category for t in Transaction.query.filter_by(user_id=user_id).all() if t.category)))
    if not all_categories:
        all_categories = ['Alimentação', 'Transporte', 'Lazer', 'Moradia', 'Educação', 'Saúde', 'Salário', 'Outros']

    return render_template(
        'reports.html',
        active_page='reports',
        transactions=transactions_data,
        cards=cards,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        month_names=month_names,
        selected_month=current_month,
        selected_year=current_year,
        years=range(2023, datetime.now().year + 2),
        expense_labels=expense_labels,
        expense_data=expense_data,
        trend_labels=trend_labels,
        trend_income_data=trend_income_data,
        trend_expense_data=trend_expense_data,
        all_categories=all_categories
    )

# Deletar uma transação
@main_bp.route('/delete_transaction/<int:transaction_id>', methods=['DELETE'])
@login_required
def delete_transaction(transaction_id):
    print(f"Recebida requisição DELETE para a transação com ID: {transaction_id}")
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != current_user.id:
        print("Erro: Usuário não autorizado para deletar esta transação.")
        return jsonify({'status': 'error', 'message': 'Você não tem permissão para deletar esta transação.'}), 403
    try:
        db.session.delete(transaction)
        db.session.commit()
        print("Sucesso: Transação deletada com sucesso!")
        return jsonify({'status': 'success', 'message': 'Transação deletada com sucesso!'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao deletar a transação: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Editar uma transação
@main_bp.route('/edit_transaction/<int:transaction_id>', methods=['POST'])
@login_required
def edit_transaction(transaction_id):
    print(f"Recebida requisição POST para a transação com ID: {transaction_id}")
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != current_user.id:
        print("Erro: Usuário não autorizado para editar esta transação.")
        return jsonify({'status': 'error', 'message': 'Você não tem permissão para editar esta transação.'}), 403

    data = request.json
    try:
        transaction.amount = float(data['amount'])
        transaction.description = data['description']
        transaction.payment_method = data['payment_method']
        transaction.category = data['category']
        transaction.type = data['type']
        
        db.session.commit()
        print("Sucesso: Transação atualizada com sucesso!")
        return jsonify({'status': 'success', 'message': 'Transação atualizada com sucesso!'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao editar a transação: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Dados inválidos, por favor, verifique os campos.'}), 400
    
# Limpar todos os dados do usuário
@main_bp.route('/clear_data', methods=['POST'])
@login_required
def clear_data():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    for transaction in transactions:
        db.session.delete(transaction)
    db.session.commit()
    flash('Todos os dados foram apagados com sucesso!', 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route("/chat")
def chat():
    return render_template("chat.html", title="Chat de Conversa", active_page="chat")

# Logout
@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado.', 'info')
    return redirect(url_for('main.login'))
