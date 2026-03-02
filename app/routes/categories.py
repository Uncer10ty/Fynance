"""Category management routes."""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import extract
from app import db
from app.models import Category, CategoryRule, Transaction
from app.services.analyzer import analyzer

categories_bp = Blueprint('categories', __name__)


@categories_bp.route('/')
def list_categories():
    """List all categories with spending totals."""
    categories = Category.query.order_by(Category.name).all()

    # Get month/year from params or default to current
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)
    
    # Calculate prev/next months
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    
    is_current_month = (year == today.year and month == today.month)
    
    # Month display name
    month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    current_month = f"{month_names[month - 1]} {year}"

    # Add spending stats to each category for the selected month
    for cat in categories:
        monthly_total = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.category_id == cat.id,
            Transaction.amount < 0,
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month
        ).scalar() or 0
        cat.monthly_total = abs(monthly_total)

    return render_template('categories/list.html', 
                           categories=categories,
                           year=year,
                           month=month,
                           current_month=current_month,
                           prev_year=prev_year,
                           prev_month=prev_month,
                           next_year=next_year,
                           next_month=next_month,
                           is_current_month=is_current_month)


@categories_bp.route('/new', methods=['GET', 'POST'])
def new_category():
    """Create a new category."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        icon = request.form.get('icon', '📁').strip()
        color = request.form.get('color', '#9E9E9E').strip()

        if not name:
            flash('Category name is required', 'error')
            return render_template('categories/new.html')

        # Check for duplicate
        if Category.query.filter_by(name=name).first():
            flash('Category already exists', 'error')
            return render_template('categories/new.html')

        category = Category(name=name, icon=icon, color=color)
        db.session.add(category)
        db.session.commit()

        flash(f'Category "{name}" created', 'success')
        return redirect(url_for('categories.list_categories'))

    return render_template('categories/new.html')


@categories_bp.route('/<int:category_id>')
def view_category(category_id):
    """View category details and spending for a month."""
    category = Category.query.get_or_404(category_id)
    
    # Get month/year from params or default to current
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)
    
    # Calculate prev/next months
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    
    is_current_month = (year == today.year and month == today.month)
    
    # Month display name
    month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    current_month = f"{month_names[month - 1]} {year}"

    # Get spending trend
    trend = analyzer.get_category_trend(category_id, months=12)
    
    # Get monthly total for this category
    monthly_total = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.category_id == category_id,
        Transaction.amount < 0,
        extract('year', Transaction.date) == year,
        extract('month', Transaction.date) == month
    ).scalar() or 0

    # Get transactions for this category in the selected month
    transactions = Transaction.query.filter(
        Transaction.category_id == category_id,
        extract('year', Transaction.date) == year,
        extract('month', Transaction.date) == month
    ).order_by(Transaction.date.desc()).all()

    # Get rules for this category
    rules = category.rules.all()

    return render_template('categories/view.html',
                           category=category,
                           trend=trend,
                           transactions=transactions,
                           rules=rules,
                           year=year,
                           month=month,
                           current_month=current_month,
                           prev_year=prev_year,
                           prev_month=prev_month,
                           next_year=next_year,
                           next_month=next_month,
                           is_current_month=is_current_month,
                           monthly_total=abs(monthly_total))


@categories_bp.route('/<int:category_id>/edit', methods=['GET', 'POST'])
def edit_category(category_id):
    """Edit category details."""
    category = Category.query.get_or_404(category_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        icon = request.form.get('icon', '📁').strip()
        color = request.form.get('color', '#9E9E9E').strip()

        if name:
            category.name = name
            category.icon = icon
            category.color = color
            db.session.commit()

            flash('Category updated', 'success')
            return redirect(url_for('categories.view_category', category_id=category_id))

    return render_template('categories/edit.html', category=category)


@categories_bp.route('/<int:category_id>/delete', methods=['POST'])
def delete_category(category_id):
    """Delete a category."""
    category = Category.query.get_or_404(category_id)

    # Don't allow deleting if transactions use it
    if category.transactions.count() > 0:
        flash('Cannot delete category with transactions. Reassign transactions first.', 'error')
        return redirect(url_for('categories.view_category', category_id=category_id))

    name = category.name
    db.session.delete(category)
    db.session.commit()

    flash(f'Category "{name}" deleted', 'success')
    return redirect(url_for('categories.list_categories'))


@categories_bp.route('/rules')
def list_rules():
    """List all categorization rules."""
    rules = CategoryRule.query.order_by(
        CategoryRule.priority.desc(),
        CategoryRule.pattern
    ).all()

    return render_template('categories/rules.html', rules=rules)


@categories_bp.route('/rules/new', methods=['GET', 'POST'])
def new_rule():
    """Create a new categorization rule."""
    categories = Category.query.order_by(Category.name).all()

    if request.method == 'POST':
        pattern = request.form.get('pattern', '').strip().upper()
        category_id = request.form.get('category_id', type=int)
        is_regex = request.form.get('is_regex', 'false') == 'true'

        if not pattern or not category_id:
            flash('Pattern and category are required', 'error')
            return render_template('categories/new_rule.html', categories=categories)

        rule = CategoryRule(
            pattern=pattern,
            category_id=category_id,
            is_regex=is_regex,
            is_user_created=True,
            priority=10
        )
        db.session.add(rule)
        db.session.commit()

        flash('Rule created', 'success')
        return redirect(url_for('categories.list_rules'))

    return render_template('categories/new_rule.html', categories=categories)


@categories_bp.route('/rules/<int:rule_id>/delete', methods=['POST'])
def delete_rule(rule_id):
    """Delete a categorization rule."""
    rule = CategoryRule.query.get_or_404(rule_id)
    db.session.delete(rule)
    db.session.commit()

    flash('Rule deleted', 'success')
    return redirect(url_for('categories.list_rules'))


@categories_bp.route('/api/list')
def api_list_categories():
    """API endpoint to list categories."""
    categories = Category.query.order_by(Category.name).all()
    return jsonify([c.to_dict() for c in categories])
