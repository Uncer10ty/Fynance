from app import create_app, db
from app.models import Category

app = create_app()


def init_default_categories():
    """Initialize default spending categories if none exist."""
    with app.app_context():
        if Category.query.count() == 0:
            default_categories = [
                # Essential
                ("Housing", "#4CAF50", "🏠"),
                ("Utilities", "#2196F3", "💡"),
                ("Groceries", "#8BC34A", "🛒"),
                ("Transport", "#FF9800", "🚗"),
                # Financial
                ("Bank Fees", "#9E9E9E", "🏦"),
                ("Savings", "#00BCD4", "💰"),
                ("Loan Repayment", "#795548", "📋"),
                # Lifestyle
                ("Dining & Takeaway", "#E91E63", "🍔"),
                ("Entertainment", "#9C27B0", "🎬"),
                ("Shopping", "#F44336", "🛍️"),
                ("Health & Wellness", "#00E676", "💊"),
                ("Travel", "#3F51B5", "✈️"),
                ("Subscriptions", "#673AB7", "📺"),
                # Income
                ("Salary", "#4CAF50", "💵"),
                ("Refund", "#8BC34A", "↩️"),
                ("Interest", "#CDDC39", "📈"),
                # Other
                ("Cash Withdrawal", "#607D8B", "💸"),
                ("Transfer", "#78909C", "🔄"),
                ("Charity", "#FF5722", "❤️"),
                ("Education", "#03A9F4", "📚"),
                ("Pets", "#A1887F", "🐾"),
                ("Uncategorized", "#BDBDBD", "❓"),
            ]

            for name, color, icon in default_categories:
                category = Category(name=name, color=color, icon=icon)
                db.session.add(category)

            db.session.commit()
            print(f"Created {len(default_categories)} default categories")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_default_categories()
    
    print("Starting Fynance - Personal Finance Tracker")
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True, port=5000)
