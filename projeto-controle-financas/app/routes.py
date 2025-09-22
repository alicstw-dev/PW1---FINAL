from flask import render_template, redirect, url_for, request, Blueprint, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from .models import User, Transaction, Card
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

# Página de Login (também usada como página inicial '/')
@main_bp.route('/', methods=['GET', 'POST'])
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            flash('Por favor, preencha todos os campos.', 'danger')
            return redirect(url_for('main.login'))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')

    return render_template('login.html')

# Página de Registro
@main_bp.route('/register', methods=['GET', 'POST'])
def register():
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
def dashboard():
    if 'user_id' not in session:
        flash('Faça login para acessar o dashboard.', 'warning')
        return redirect(url_for('main.login'))

    user_id = session['user_id']
    
    # Adicionando um filtro para o mês e ano
    try:
        selected_month = int(request.args.get('month', datetime.now().month))
        selected_year = int(request.args.get('year', datetime.now().year))
    except (ValueError, TypeError):
        selected_month = datetime.now().month
        selected_year = datetime.now().year
    
    # Filtrar transações por mês e ano
    transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        extract('month', Transaction.date) == selected_month,
        extract('year', Transaction.date) == selected_year
    ).order_by(Transaction.date.desc()).all()

    # Calcular saldos com base nas transações filtradas
    total_income = sum(t.amount for t in transactions if t.type == 'income')
    total_expense = sum(t.amount for t in transactions if t.type == 'expense')
    balance = total_income - total_expense

    # Obter anos disponíveis para o seletor
    years = sorted(list(set(t.date.year for t in Transaction.query.filter_by(user_id=user_id).all())))
    if not years:
        years = [datetime.now().year]

    # Nomes dos meses para o seletor
    month_names = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

    # Faturas de cartão de crédito do mês atual
    credit_card_bill = sum(t.amount for t in transactions if t.payment_method == 'Cartao de Credito' and t.type == 'expense')
    
    invoices = [] # Lógica para buscar faturas de cartões de crédito aqui

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

# Adicionar Transação (agora apenas para despesas)
@main_bp.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if 'user_id' not in session:
        flash('Faça login para adicionar transações.', 'warning')
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        # Lógica para lidar com o envio do formulário (POST)
        type_ = request.form.get('type')
        amount = request.form.get('amount')
        description = request.form.get('description', '')
        payment_method = request.form.get('payment_method')
        category = request.form.get('category')

        if not type_ or not amount or not payment_method or not category:
            flash('Por favor, preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('main.add_transaction'))

        try:
            amount = float(amount)
        except (ValueError, TypeError):
            flash('O valor da transação deve ser um número válido.', 'danger')
            return redirect(url_for('main.add_transaction'))

        new_transaction = Transaction(
            type=type_,
            amount=amount,
            description=description,
            payment_method=payment_method,
            category=category,
            user_id=session['user_id']
        )
        db.session.add(new_transaction)
        db.session.commit()

        flash('Transação adicionada com sucesso!', 'success')
        return redirect(url_for('main.dashboard'))
    else:
        # Lógica para exibir a página (GET)
        return render_template('add_transaction.html', active_page='add')

# Nova Rota para Adicionar Renda Fixa
@main_bp.route('/add_income', methods=['POST'])
def add_income():
    if 'user_id' not in session:
        flash('Faça login para adicionar renda.', 'warning')
        return redirect(url_for('main.login'))

    income_value = request.form.get('income_value')
    if not income_value:
        flash('Por favor, insira um valor para a renda.', 'danger')
        return redirect(url_for('main.add_transaction'))
    
    try:
        amount = float(income_value)
    except (ValueError, TypeError):
        flash('O valor da renda deve ser um número válido.', 'danger')
        return redirect(url_for('main.add_transaction'))

    new_income_transaction = Transaction(
        type='income',
        amount=amount,
        description='Renda Fixa',
        payment_method='Transferencia',
        category='Salario',
        user_id=session['user_id']
    )
    db.session.add(new_income_transaction)
    db.session.commit()

    flash('Renda fixa adicionada com sucesso!', 'success')
    return redirect(url_for('main.dashboard'))

# Nova Rota para Adicionar Cartão
@main_bp.route('/add_card', methods=['POST'])
def add_card():
    if 'user_id' not in session:
        flash('Faça login para adicionar um cartão.', 'warning')
        return redirect(url_for('main.login'))
    
    from .models import Card

    card_name = request.form.get('card_name')
    card_due_day = request.form.get('card_due_day')

    if not card_name or not card_due_day:
        flash('Por favor, preencha todos os campos do cartão.', 'danger')
        return redirect(url_for('main.add_transaction'))
    
    try:
        due_day = int(card_due_day)
        if not 1 <= due_day <= 31:
            raise ValueError("Dia de fechamento inválido.")
    except (ValueError, TypeError):
        flash('O dia de fechamento do cartão deve ser um número entre 1 e 31.', 'danger')
        return redirect(url_for('main.add_transaction'))
    
    new_card = Card(
        name=card_name,
        due_day=due_day,
        user_id=session['user_id']
    )
    db.session.add(new_card)
    db.session.commit()

    flash('Cartão adicionado com sucesso!', 'success')
    return redirect(url_for('main.dashboard'))

# Relatórios
@main_bp.route('/reports')
def reports():
    if 'user_id' not in session:
        flash('Faça login para ver relatórios.', 'warning')
        return redirect(url_for('main.login'))

    user_id = session['user_id']

    try:
        current_year = int(request.args.get('year', datetime.now().year))
        current_month = int(request.args.get('month', datetime.now().month))
    except (ValueError, TypeError):
        current_year = datetime.now().year
        current_month = datetime.now().month
        flash('Filtro de data inválido. Exibindo dados do mês atual.', 'warning')

    start_date = datetime(current_year, current_month, 1)
    end_date = datetime(current_year, current_month, monthrange(current_year, current_month)[1])

    transactions = Transaction.query.filter_by(user_id=user_id) \
                                   .filter(Transaction.date.between(start_date, end_date)) \
                                   .order_by(Transaction.date.desc()) \
                                   .all()
    
    # Prepara os dados para o gráfico de despesas por categoria
    expenses_by_category = defaultdict(float)
    for transaction in transactions:
        if transaction.type == 'expense':
            expenses_by_category[transaction.category] += transaction.amount
    
    expense_labels = list(expenses_by_category.keys())
    expense_data = list(expenses_by_category.values())

    # Prepara os dados para o gráfico de Receitas vs Despesas
    trend_income = defaultdict(float)
    trend_expense = defaultdict(float)
    dates_sorted = sorted(list(set(t.date for t in transactions)))
    trend_labels = [d.strftime('%d/%m') for d in dates_sorted]

    for transaction in transactions:
        date_str = transaction.date.strftime('%d/%m')
        if transaction.type == 'income':
            trend_income[date_str] += transaction.amount
        else:
            trend_expense[date_str] += transaction.amount
    
    trend_income_data = [trend_income[label] for label in trend_labels]
    trend_expense_data = [trend_expense[label] for label in trend_labels]
    
    # Converte os objetos de transação para uma lista de dicionários
    transactions_data = [{
        'id': t.id,
        'type': t.type,
        'amount': t.amount,
        'description': t.description,
        'payment_method': t.payment_method,
        'category': t.category,
        'date': t.date.isoformat()  # Converte a data para uma string ISO
    } for t in transactions]

    cards = Card.query.filter_by(user_id=user_id).all()

    total_income = sum(t.amount for t in transactions if t.type == 'income')
    total_expense = sum(t.amount for t in transactions if t.type == 'expense')
    balance = total_income - total_expense

    month_names = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    return render_template(
        'reports.html',
        active_page='reports',
        transactions=transactions_data,  # Passa a lista de dicionários serializáveis
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
        trend_expense_data=trend_expense_data
    )

# Logout
@main_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logout realizado.', 'info')
    return redirect(url_for('main.login'))
