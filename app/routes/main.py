"""Main routes - Dashboard and home page."""
from datetime import date
from calendar import monthrange
from flask import Blueprint, render_template, request
from app.services.analyzer import analyzer
from app.models import Account, Transaction, Category

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def dashboard():
    """Main dashboard showing spending overview."""
    today = date.today()
    
    # Get year/month from query params, default to current
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)
    
    # Validate month/year
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1
    
    # Calculate prev/next month
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    # Check if viewing current month
    is_current_month = (year == today.year and month == today.month)
    
    # Check if transfers should be excluded
    exclude_transfers = request.args.get('exclude_transfers', 'false') == 'true'

    # Get selected month summary
    monthly_summary = analyzer.get_monthly_summary(year, month, exclude_transfers=exclude_transfers)

    # Get monthly comparison for chart
    monthly_comparison = analyzer.get_monthly_comparison(6)

    # Get account balances
    accounts = analyzer.get_account_balances()

    # Get recent transactions
    recent_transactions = analyzer.get_recent_transactions(10)

    # Count items needing review
    uncategorized_count = Transaction.query.filter(
        Transaction.category_id == None
    ).count()

    # Format month name
    month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    current_month_name = f"{month_names[month]} {year}"
    
    return render_template('dashboard.html',
                           summary=monthly_summary,
                           monthly_comparison=monthly_comparison,
                           accounts=accounts,
                           recent_transactions=recent_transactions,
                           uncategorized_count=uncategorized_count,
                           current_month=current_month_name,
                           year=year,
                           month=month,
                           prev_year=prev_year,
                           prev_month=prev_month,
                           next_year=next_year,
                           next_month=next_month,
                           is_current_month=is_current_month,
                           exclude_transfers=exclude_transfers)
