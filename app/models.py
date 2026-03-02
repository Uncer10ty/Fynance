from datetime import datetime
from app import db


class Account(db.Model):
    """Bank account model."""
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    bank = db.Column(db.String(100))
    account_number = db.Column(db.String(50))
    currency = db.Column(db.String(3), default='GBP')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='account', lazy='dynamic')
    imports = db.relationship('Import', backref='account', lazy='dynamic')

    def __repr__(self):
        return f'<Account {self.name}>'

    @property
    def balance(self):
        """Calculate current balance from transactions."""
        result = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.account_id == self.id
        ).scalar()
        return result or 0

    @property
    def transaction_count(self):
        return self.transactions.count()


class Category(db.Model):
    """Spending category model."""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    icon = db.Column(db.String(10))
    color = db.Column(db.String(7))  # Hex color

    parent = db.relationship('Category', remote_side=[id], backref='subcategories')
    transactions = db.relationship('Transaction', backref='category', lazy='dynamic')
    rules = db.relationship('CategoryRule', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'color': self.color
        }


class Transaction(db.Model):
    """Financial transaction model."""
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # Negative for expenses
    balance = db.Column(db.Float, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    original_description = db.Column(db.String(500))
    notes = db.Column(db.Text)
    is_reviewed = db.Column(db.Boolean, default=False)
    import_id = db.Column(db.Integer, db.ForeignKey('imports.id'), nullable=True)
    hash = db.Column(db.String(64), unique=True)  # For deduplication
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Transaction {self.date} {self.amount}>'

    @property
    def is_expense(self):
        return self.amount < 0

    @property
    def is_income(self):
        return self.amount > 0

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'description': self.description,
            'amount': self.amount,
            'category': self.category.to_dict() if self.category else None,
            'account': self.account.name if self.account else None,
            'is_reviewed': self.is_reviewed
        }


class CategoryRule(db.Model):
    """Rule for auto-categorizing transactions."""
    __tablename__ = 'category_rules'

    id = db.Column(db.Integer, primary_key=True)
    pattern = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    priority = db.Column(db.Integer, default=0)
    is_regex = db.Column(db.Boolean, default=False)
    is_user_created = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CategoryRule {self.pattern} -> {self.category.name}>'


class Import(db.Model):
    """Record of statement imports."""
    __tablename__ = 'imports'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    filename = db.Column(db.String(255))
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    transaction_count = db.Column(db.Integer, default=0)
    duplicates_skipped = db.Column(db.Integer, default=0)

    transactions = db.relationship('Transaction', backref='import_record', lazy='dynamic')

    def __repr__(self):
        return f'<Import {self.filename}>'
