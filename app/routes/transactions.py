"""Transaction management routes."""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import extract
from app import db
from app.models import Transaction, Category, Account
from app.services.categorizer import learn_category, categorizer
from app.services.analyzer import analyzer

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('/')
def list_transactions():
    """List all transactions with filtering."""
    # Get filter parameters
    account_id = request.args.get('account_id', type=int)
    category_id = request.args.get('category_id', type=int)
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    search = request.args.get('search', '').strip()

    # Build query
    query = Transaction.query

    if account_id:
        query = query.filter(Transaction.account_id == account_id)

    if category_id:
        query = query.filter(Transaction.category_id == category_id)

    if year:
        query = query.filter(extract('year', Transaction.date) == year)

    if month:
        query = query.filter(extract('month', Transaction.date) == month)

    if search:
        query = query.filter(Transaction.description.ilike(f'%{search}%'))

    transactions = query.order_by(Transaction.date.desc()).limit(200).all()

    # Get filter options
    accounts = Account.query.all()
    categories = Category.query.order_by(Category.name).all()

    return render_template('transactions/list.html',
                           transactions=transactions,
                           accounts=accounts,
                           categories=categories,
                           filters={
                               'account_id': account_id,
                               'category_id': category_id,
                               'year': year,
                               'month': month,
                               'search': search
                           })


@transactions_bp.route('/review')
def review():
    """Review and categorize transactions."""
    # Get transactions needing review
    transactions = analyzer.get_unreviewed_transactions(50)
    categories = Category.query.order_by(Category.name).all()

    return render_template('transactions/review.html',
                           transactions=transactions,
                           categories=categories)


@transactions_bp.route('/<int:transaction_id>/categorize', methods=['POST'])
def categorize(transaction_id):
    """Categorize a single transaction."""
    transaction = Transaction.query.get_or_404(transaction_id)

    category_id = request.form.get('category_id', type=int)
    learn = request.form.get('learn', 'false') == 'true'

    if category_id:
        transaction.category_id = category_id
        transaction.is_reviewed = True
        db.session.commit()

        # Learn from this categorization if requested
        if learn:
            learn_category(transaction.description, category_id)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})

        flash('Transaction categorized', 'success')

    return redirect(url_for('transactions.review'))


@transactions_bp.route('/recategorize', methods=['POST'])
def recategorize():
    """Re-run auto-categorization on transactions."""
    mode = request.form.get('mode', 'uncategorized')  # 'uncategorized' or 'all'
    
    # Reload rules to pick up any new ones
    categorizer.load_rules()
    
    if mode == 'all':
        # Reset and recategorize all transactions
        transactions = Transaction.query.all()
        for tx in transactions:
            tx.category_id = None
            tx.is_reviewed = False
    else:
        # Only uncategorized transactions
        transactions = Transaction.query.filter(Transaction.category_id == None).all()
    
    # Run categorization
    stats = categorizer.categorize_transactions(transactions)
    db.session.commit()
    
    flash(f"Re-categorized {stats['categorized']} transactions, {stats['uncategorized']} still need review", 'success')
    
    return redirect(url_for('transactions.review'))


@transactions_bp.route('/bulk-categorize', methods=['POST'])
def bulk_categorize():
    """Categorize multiple transactions at once."""
    data = request.get_json()

    if not data or 'transactions' not in data:
        return jsonify({'error': 'Invalid request'}), 400

    categorized = 0
    for item in data['transactions']:
        transaction_id = item.get('id')
        category_id = item.get('category_id')

        if transaction_id and category_id:
            transaction = Transaction.query.get(transaction_id)
            if transaction:
                transaction.category_id = category_id
                transaction.is_reviewed = True
                categorized += 1

                # Optionally learn
                if item.get('learn'):
                    learn_category(transaction.description, category_id)

    db.session.commit()

    return jsonify({
        'success': True,
        'categorized': categorized
    })


@transactions_bp.route('/<int:transaction_id>', methods=['GET'])
def view_transaction(transaction_id):
    """View transaction details."""
    transaction = Transaction.query.get_or_404(transaction_id)
    categories = Category.query.order_by(Category.name).all()
    
    # Preserve filter params for back navigation
    filters = {
        'account_id': request.args.get('account_id', type=int),
        'category_id': request.args.get('category_id', type=int),
        'year': request.args.get('year', type=int),
        'month': request.args.get('month', type=int),
        'search': request.args.get('search', '')
    }

    return render_template('transactions/view.html',
                           transaction=transaction,
                           categories=categories,
                           filters=filters)


@transactions_bp.route('/<int:transaction_id>/update', methods=['POST'])
def update_transaction(transaction_id):
    """Update transaction details."""
    transaction = Transaction.query.get_or_404(transaction_id)

    category_id = request.form.get('category_id', type=int)
    notes = request.form.get('notes', '').strip()

    if category_id:
        transaction.category_id = category_id
        transaction.is_reviewed = True

    transaction.notes = notes
    db.session.commit()

    flash('Transaction updated', 'success')
    
    # Redirect back with filter params preserved
    filter_params = {}
    for key in ['account_id', 'category_id', 'year', 'month', 'search']:
        val = request.form.get(f'filter_{key}')
        if val:
            filter_params[key] = val
    
    return redirect(url_for('transactions.list_transactions', **filter_params))


@transactions_bp.route('/monthly/<int:year>/<int:month>')
def monthly_view(year, month):
    """View transactions for a specific month."""
    summary = analyzer.get_monthly_summary(year, month)

    transactions = Transaction.query.filter(
        extract('year', Transaction.date) == year,
        extract('month', Transaction.date) == month
    ).order_by(Transaction.date.desc()).all()

    return render_template('transactions/monthly.html',
                           year=year,
                           month=month,
                           summary=summary,
                           transactions=transactions)
