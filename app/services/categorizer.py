"""
Transaction categorization service.
Uses keyword matching and learns from user input.
"""
import re
from app import db
from app.models import Category, CategoryRule, Transaction


# Default categorization rules (keyword -> category name)
DEFAULT_RULES = {
    # Groceries
    'Groceries': [
        'TESCO', 'SAINSBURY', 'ASDA', 'MORRISONS', 'ALDI', 'LIDL', 'WAITROSE',
        'CO-OP', 'COOP', 'M&S FOOD', 'MARKS SPENCER', 'ICELAND', 'OCADO',
        'FARMFOODS', 'COSTCO', 'WHOLE FOODS'
    ],
    # Transport
    'Transport': [
        'TFL', 'TRANSPORT FOR LONDON', 'TRAINLINE', 'NATIONAL RAIL',
        'UBER', 'LYFT', 'BOLT', 'SHELL', 'BP', 'ESSO', 'TEXACO', 'TOTAL',
        'PETROL', 'PARKING', 'NCP', 'DVLA', 'RAC', 'AA '
    ],
    # Dining & Takeaway
    'Dining & Takeaway': [
        'DELIVEROO', 'JUST EAT', 'UBER EATS', 'MCDONALDS', 'BURGER KING',
        'KFC', 'SUBWAY', 'NANDOS', 'PIZZA', 'GREGGS', 'COSTA', 'STARBUCKS',
        'PRET', 'CAFFE NERO', 'RESTAURANT', 'CAFE', 'COFFEE', 'PUB ', 'BAR '
    ],
    # Subscriptions
    'Subscriptions': [
        'NETFLIX', 'SPOTIFY', 'AMAZON PRIME', 'DISNEY PLUS', 'DISNEY+',
        'APPLE.COM', 'GOOGLE STORAGE', 'DROPBOX', 'MICROSOFT 365',
        'YOUTUBE PREMIUM', 'HBO', 'NOW TV', 'SKY', 'VIRGIN MEDIA',
        'BT GROUP', 'OPENREACH', 'GYM', 'FITNESS'
    ],
    # Shopping
    'Shopping': [
        'AMAZON', 'EBAY', 'ARGOS', 'JOHN LEWIS', 'CURRYS', 'PC WORLD',
        'NEXT', 'PRIMARK', 'H&M', 'ZARA', 'ASOS', 'BOOTS', 'SUPERDRUG',
        'IKEA', 'B&Q', 'SCREWFIX', 'HOMEBASE', 'WILKO'
    ],
    # Utilities
    'Utilities': [
        'BRITISH GAS', 'EDF', 'EON', 'OCTOPUS ENERGY', 'BULB', 'SSE',
        'SCOTTISH POWER', 'THAMES WATER', 'ANGLIAN WATER', 'SEVERN TRENT',
        'VODAFONE', 'EE ', 'O2 ', 'THREE', 'GIFFGAFF', 'PLUSNET', 'TALKTALK'
    ],
    # Health & Wellness
    'Health & Wellness': [
        'PHARMACY', 'CHEMIST', 'LLOYDS PHARMACY', 'NHS', 'DOCTOR', 'DENTIST',
        'OPTICIAN', 'SPECSAVERS', 'VISION EXPRESS'
    ],
    # Entertainment
    'Entertainment': [
        'CINEMA', 'ODEON', 'VUE', 'CINEWORLD', 'THEATRE', 'TICKETMASTER',
        'EVENTBRITE', 'STEAM', 'PLAYSTATION', 'XBOX', 'NINTENDO'
    ],
    # Travel
    'Travel': [
        'RYANAIR', 'EASYJET', 'BRITISH AIRWAYS', 'BOOKING.COM', 'AIRBNB',
        'HOTELS.COM', 'EXPEDIA', 'SKYSCANNER', 'EUROSTAR'
    ],
    # Income
    'Salary': [
        'SALARY', 'WAGES', 'PAYROLL', 'BACS'
    ],
    # Refunds
    'Refund': [
        'REFUND', 'REVERSAL', 'CASHBACK'
    ],
    # Cash
    'Cash Withdrawal': [
        'ATM', 'CASH', 'WITHDRAWAL', 'CASHPOINT'
    ],
    # Transfers
    'Transfer': [
        'TRANSFER', 'TFR', 'STANDING ORDER', 'DIRECT DEBIT'
    ],
    # Housing
    'Housing': [
        'RENT', 'MORTGAGE', 'COUNCIL TAX', 'INSURANCE'
    ],
    # Charity
    'Charity': [
        'CHARITY', 'DONATION', 'RED CROSS', 'OXFAM', 'UNICEF', 'WWF'
    ],
    # Interest
    'Interest': [
        'INTEREST', 'INTEREST ON CASH'
    ]
}


class TransactionCategorizer:
    """Categorize transactions using rules and learning."""

    def __init__(self):
        self.rules_cache = None

    def load_rules(self) -> list[dict]:
        """Load all categorization rules from database."""
        rules = CategoryRule.query.order_by(CategoryRule.priority.desc()).all()

        # Convert to list of dicts with category info
        self.rules_cache = []
        for rule in rules:
            self.rules_cache.append({
                'pattern': rule.pattern.upper(),
                'category_id': rule.category_id,
                'is_regex': rule.is_regex,
                'priority': rule.priority
            })

        return self.rules_cache

    def initialize_default_rules(self):
        """Initialize default categorization rules in database."""
        if CategoryRule.query.count() > 0:
            return  # Rules already exist

        for category_name, keywords in DEFAULT_RULES.items():
            category = Category.query.filter_by(name=category_name).first()
            if not category:
                continue

            for keyword in keywords:
                rule = CategoryRule(
                    pattern=keyword,
                    category_id=category.id,
                    priority=0,
                    is_regex=False,
                    is_user_created=False
                )
                db.session.add(rule)

        db.session.commit()

    def match_category(self, description: str, notes: str = '') -> int | None:
        """Find matching category for a transaction description or notes."""
        if self.rules_cache is None:
            self.load_rules()

        description_upper = description.upper()
        notes_upper = (notes or '').upper()
        # Combine description and notes for matching
        combined_text = f"{description_upper} {notes_upper}"

        for rule in self.rules_cache:
            if rule['is_regex']:
                try:
                    if re.search(rule['pattern'], combined_text, re.IGNORECASE):
                        return rule['category_id']
                except re.error:
                    continue
            else:
                if rule['pattern'] in combined_text:
                    return rule['category_id']

        return None

    def categorize_transaction(self, transaction: Transaction) -> bool:
        """
        Attempt to categorize a single transaction.
        Returns True if category was found, False otherwise.
        """
        if transaction.category_id is not None:
            return True

        # Check both description and notes for category matching
        notes = getattr(transaction, 'notes', '') or ''
        category_id = self.match_category(transaction.description, notes)

        if category_id:
            transaction.category_id = category_id
            transaction.is_reviewed = False  # Auto-categorized, not user-reviewed
            return True

        return False

    def categorize_transactions(self, transactions: list[Transaction]) -> dict:
        """
        Categorize a list of transactions.
        Returns stats about categorization.
        """
        self.load_rules()  # Refresh rules

        categorized = 0
        uncategorized = 0

        for transaction in transactions:
            if self.categorize_transaction(transaction):
                categorized += 1
            else:
                uncategorized += 1

        return {
            'categorized': categorized,
            'uncategorized': uncategorized,
            'total': len(transactions)
        }

    def learn_from_user(self, description: str, category_id: int):
        """
        Create a new rule based on user categorization.
        Extracts key merchant name from description.
        """
        # Clean up description - extract likely merchant name
        # Remove common suffixes like dates, reference numbers
        cleaned = description.upper()

        # Remove common patterns
        patterns_to_remove = [
            r'\d{2}/\d{2}/\d{2,4}',  # Dates
            r'\d{4,}',  # Long numbers (references)
            r'\s+\d+$',  # Trailing numbers
            r'\s+(ON|AT|IN|TO|FROM)\s+.*$',  # Location/date info
        ]

        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned)

        cleaned = cleaned.strip()

        # Only create rule if we have a meaningful pattern
        if len(cleaned) < 3:
            return None

        # Check if rule already exists
        existing = CategoryRule.query.filter_by(pattern=cleaned).first()
        if existing:
            # Update existing rule
            existing.category_id = category_id
            db.session.commit()
            return existing

        # Create new rule with high priority (user rules take precedence)
        rule = CategoryRule(
            pattern=cleaned,
            category_id=category_id,
            priority=10,
            is_regex=False,
            is_user_created=True
        )
        db.session.add(rule)
        db.session.commit()

        # Refresh cache
        self.rules_cache = None

        return rule


# Global categorizer instance
categorizer = TransactionCategorizer()


def categorize_transaction(transaction: Transaction) -> bool:
    """Convenience function to categorize a single transaction."""
    return categorizer.categorize_transaction(transaction)


def categorize_transactions(transactions: list[Transaction]) -> dict:
    """Convenience function to categorize multiple transactions."""
    return categorizer.categorize_transactions(transactions)


def learn_category(description: str, category_id: int):
    """Learn a new categorization rule from user input."""
    return categorizer.learn_from_user(description, category_id)
