"""
Spending analysis service.
Provides insights into spending patterns.
"""
from datetime import datetime, date
from calendar import monthrange
from sqlalchemy import func, extract
from app import db
from app.models import Transaction, Category, Account


class SpendingAnalyzer:
    """Analyze spending patterns."""

    def get_monthly_summary(self, year: int, month: int, account_id: int = None, exclude_transfers: bool = False) -> dict:
        """Get spending summary for a specific month."""
        # Build base query
        query = Transaction.query.filter(
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month
        )

        if account_id:
            query = query.filter(Transaction.account_id == account_id)

        transactions = query.all()
        
        # Get Transfer category ID for filtering
        transfer_category_id = None
        if exclude_transfers:
            transfer_cat = Category.query.filter_by(name='Transfer').first()
            if transfer_cat:
                transfer_category_id = transfer_cat.id

        # Calculate totals
        total_expenses = 0
        total_income = 0
        filtered_transactions = []
        
        for t in transactions:
            # Skip transfers if requested
            if exclude_transfers and t.category_id == transfer_category_id:
                continue
            filtered_transactions.append(t)
            if t.amount < 0:
                total_expenses += t.amount
            else:
                total_income += t.amount

        # Group by category
        category_spending = {}
        for t in filtered_transactions:
            if t.amount >= 0:  # Skip income for category breakdown
                continue

            cat_name = t.category.name if t.category else 'Uncategorized'
            cat_color = t.category.color if t.category else '#BDBDBD'
            cat_icon = t.category.icon if t.category else '❓'

            if cat_name not in category_spending:
                category_spending[cat_name] = {
                    'name': cat_name,
                    'color': cat_color,
                    'icon': cat_icon,
                    'amount': 0,
                    'count': 0
                }

            category_spending[cat_name]['amount'] += abs(t.amount)
            category_spending[cat_name]['count'] += 1

        # Sort by amount
        categories_sorted = sorted(
            category_spending.values(),
            key=lambda x: x['amount'],
            reverse=True
        )

        return {
            'year': year,
            'month': month,
            'total_expenses': abs(total_expenses),
            'total_income': total_income,
            'net': total_income + total_expenses,
            'transaction_count': len(filtered_transactions),
            'categories': categories_sorted
        }

    def get_category_trend(self, category_id: int, months: int = 6) -> list[dict]:
        """Get spending trend for a category over recent months."""
        today = date.today()
        trends = []

        for i in range(months - 1, -1, -1):
            # Calculate month offset
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1

            total = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.category_id == category_id,
                Transaction.amount < 0,
                extract('year', Transaction.date) == year,
                extract('month', Transaction.date) == month
            ).scalar() or 0

            trends.append({
                'year': year,
                'month': month,
                'amount': abs(total)
            })

        return trends

    def get_all_time_stats(self, account_id: int = None) -> dict:
        """Get all-time spending statistics."""
        query = Transaction.query

        if account_id:
            query = query.filter(Transaction.account_id == account_id)

        transactions = query.all()

        total_expenses = sum(t.amount for t in transactions if t.amount < 0)
        total_income = sum(t.amount for t in transactions if t.amount > 0)

        # Get date range
        dates = [t.date for t in transactions]
        min_date = min(dates) if dates else None
        max_date = max(dates) if dates else None

        return {
            'total_expenses': abs(total_expenses),
            'total_income': total_income,
            'net': total_income + total_expenses,
            'transaction_count': len(transactions),
            'date_range': {
                'start': min_date.isoformat() if min_date else None,
                'end': max_date.isoformat() if max_date else None
            }
        }

    def get_recent_transactions(self, limit: int = 10, account_id: int = None) -> list[dict]:
        """Get most recent transactions."""
        query = Transaction.query.order_by(Transaction.date.desc())

        if account_id:
            query = query.filter(Transaction.account_id == account_id)

        transactions = query.limit(limit).all()

        return [t.to_dict() for t in transactions]

    def get_uncategorized_transactions(self, limit: int = 50) -> list[Transaction]:
        """Get transactions that need categorization."""
        return Transaction.query.filter(
            Transaction.category_id == None
        ).order_by(Transaction.date.desc()).limit(limit).all()

    def get_unreviewed_transactions(self, limit: int = 50) -> list[Transaction]:
        """Get transactions that haven't been reviewed by user."""
        # Get uncategorized first, then auto-categorized but unreviewed
        uncategorized = Transaction.query.filter(
            Transaction.category_id == None
        ).order_by(Transaction.date.desc()).all()

        unreviewed = Transaction.query.filter(
            Transaction.category_id != None,
            Transaction.is_reviewed == False
        ).order_by(Transaction.date.desc()).all()

        combined = uncategorized + unreviewed
        return combined[:limit]

    def get_monthly_comparison(self, months: int = 6) -> list[dict]:
        """Get month-over-month spending comparison."""
        today = date.today()
        comparison = []

        for i in range(months - 1, -1, -1):
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1

            summary = self.get_monthly_summary(year, month)
            comparison.append({
                'year': year,
                'month': month,
                'expenses': summary['total_expenses'],
                'income': summary['total_income'],
                'net': summary['net']
            })

        return comparison

    def get_account_balances(self) -> list[dict]:
        """Get current balance for all accounts."""
        accounts = Account.query.all()
        return [
            {
                'id': a.id,
                'name': a.name,
                'bank': a.bank,
                'balance': a.balance,
                'transaction_count': a.transaction_count
            }
            for a in accounts
        ]


# Global analyzer instance
analyzer = SpendingAnalyzer()
