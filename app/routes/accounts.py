"""Account management routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import Account

accounts_bp = Blueprint('accounts', __name__)


@accounts_bp.route('/')
def list_accounts():
    """List all accounts."""
    accounts = Account.query.all()
    return render_template('accounts/list.html', accounts=accounts)


@accounts_bp.route('/new', methods=['GET', 'POST'])
def new_account():
    """Create a new account."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        bank = request.form.get('bank', '').strip()
        account_number = request.form.get('account_number', '').strip()
        currency = request.form.get('currency', 'GBP').strip()

        if not name:
            flash('Account name is required', 'error')
            return render_template('accounts/new.html')

        account = Account(
            name=name,
            bank=bank,
            account_number=account_number,
            currency=currency
        )
        db.session.add(account)
        db.session.commit()

        flash(f'Account "{name}" created successfully', 'success')
        return redirect(url_for('accounts.list_accounts'))

    return render_template('accounts/new.html')


@accounts_bp.route('/<int:account_id>')
def view_account(account_id):
    """View account details and transactions."""
    account = Account.query.get_or_404(account_id)
    transactions = account.transactions.order_by(
        db.desc('date')
    ).limit(100).all()

    return render_template('accounts/view.html',
                           account=account,
                           transactions=transactions)


@accounts_bp.route('/<int:account_id>/delete', methods=['POST'])
def delete_account(account_id):
    """Delete an account and all its transactions."""
    account = Account.query.get_or_404(account_id)
    name = account.name

    db.session.delete(account)
    db.session.commit()

    flash(f'Account "{name}" deleted', 'success')
    return redirect(url_for('accounts.list_accounts'))


@accounts_bp.route('/api/list')
def api_list_accounts():
    """API endpoint to list accounts."""
    accounts = Account.query.all()
    return jsonify([
        {
            'id': a.id,
            'name': a.name,
            'bank': a.bank
        }
        for a in accounts
    ])
