"""
Bank statement parser service.
Handles CSV and Excel files from various UK banks.
"""
import hashlib
import pandas as pd
from datetime import datetime
from dateutil import parser as date_parser


# Known bank format configurations
BANK_FORMATS = {
    'barclays': {
        'date_col': 'Date',
        'description_col': 'Description',
        'amount_col': 'Amount',
        'balance_col': 'Balance',
        'date_format': '%d/%m/%Y'
    },
    'hsbc': {
        'date_col': 'Date',
        'description_col': 'Description',
        'debit_col': 'Paid Out',
        'credit_col': 'Paid In',
        'balance_col': 'Balance',
        'date_format': '%d %b %Y'
    },
    'lloyds': {
        'date_col': 'Transaction Date',
        'description_col': 'Transaction Description',
        'debit_col': 'Debit Amount',
        'credit_col': 'Credit Amount',
        'balance_col': 'Balance',
        'date_format': '%d/%m/%Y'
    },
    'nationwide': {
        'date_col': 'Date',
        'description_col': 'Description',
        'debit_col': 'Paid out',
        'credit_col': 'Paid in',
        'balance_col': 'Balance',
        'date_format': '%d %b %Y'
    },
    'monzo': {
        'date_col': 'Date',
        'description_col': 'Name',
        'amount_col': 'Amount',
        'balance_col': 'Balance',
        'date_format': '%d/%m/%Y',
        'category_col': 'Category'
    },
    'starling': {
        'date_col': 'Date',
        'description_col': 'Counter Party',
        'amount_col': 'Amount (GBP)',
        'balance_col': 'Balance (GBP)',
        'date_format': '%d/%m/%Y'
    },
    'natwest': {
        'date_col': 'Date',
        'description_col': 'Description',
        'amount_col': 'Value',
        'balance_col': 'Balance',
        'date_format': '%d/%m/%Y'
    }
}


class StatementParser:
    """Parse bank statements from CSV/Excel files."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df = None
        self.detected_format = None

    def load_file(self) -> pd.DataFrame:
        """Load CSV or Excel file into DataFrame."""
        if self.file_path.endswith('.csv'):
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    self.df = pd.read_csv(self.file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
        elif self.file_path.endswith(('.xlsx', '.xls')):
            self.df = pd.read_excel(self.file_path)
        else:
            raise ValueError(f"Unsupported file format: {self.file_path}")

        # Clean column names
        self.df.columns = self.df.columns.str.strip()
        return self.df

    def detect_bank_format(self) -> str:
        """Attempt to detect which bank format the file uses."""
        if self.df is None:
            self.load_file()

        columns = set(self.df.columns.str.lower())

        # Check for Monzo-specific columns
        if 'name' in columns and 'category' in columns:
            return 'monzo'

        # Check for Starling-specific columns
        if 'counter party' in columns:
            return 'starling'

        # Check for HSBC pattern
        if 'paid out' in columns and 'paid in' in columns:
            return 'hsbc'

        # Check for Lloyds pattern
        if 'transaction date' in columns and 'transaction description' in columns:
            return 'lloyds'

        # Check for Nationwide pattern
        if 'paid out' in columns and 'paid in' in columns:
            return 'nationwide'

        # Default to generic format
        return 'generic'

    def get_column_mapping(self, bank_format: str = None) -> dict:
        """Get column mapping for the detected or specified format."""
        if bank_format and bank_format in BANK_FORMATS:
            return BANK_FORMATS[bank_format]

        # Generic mapping - try to find common column names
        columns = {col.lower(): col for col in self.df.columns}

        mapping = {}

        # Date column
        for key in ['date', 'transaction date', 'trans date', 'posting date']:
            if key in columns:
                mapping['date_col'] = columns[key]
                break

        # Description column
        for key in ['description', 'transaction description', 'name', 'narrative', 'details', 'memo', 'counter party']:
            if key in columns:
                mapping['description_col'] = columns[key]
                break

        # Amount column (single)
        for key in ['amount', 'value', 'transaction amount']:
            if key in columns:
                mapping['amount_col'] = columns[key]
                break

        # Debit/Credit columns
        for key in ['debit', 'debit amount', 'paid out', 'money out', 'withdrawals']:
            if key in columns:
                mapping['debit_col'] = columns[key]
                break

        for key in ['credit', 'credit amount', 'paid in', 'money in', 'deposits']:
            if key in columns:
                mapping['credit_col'] = columns[key]
                break

        # Balance column
        for key in ['balance', 'running balance', 'available balance']:
            if key in columns:
                mapping['balance_col'] = columns[key]
                break

        # Notes/memo column (for additional description info)
        for key in ['notes', 'memo', 'note', 'action', 'type', 'transaction type']:
            if key in columns:
                mapping['notes_col'] = columns[key]
                break

        # Bank-provided category column
        for key in ['category', 'transaction category', 'spending category']:
            if key in columns:
                mapping['category_col'] = columns[key]
                break

        return mapping

    def parse_date(self, date_val, date_format: str = None) -> datetime.date:
        """Parse date from various formats, including datetime with time."""
        if pd.isna(date_val):
            return None

        if isinstance(date_val, datetime):
            return date_val.date()

        date_str = str(date_val).strip()
        
        # Strip time component if present (e.g., "01/09/2025 10:53" -> "01/09/2025")
        # Handle common datetime separators
        if ' ' in date_str:
            # Check if the part after space looks like a time (contains :)
            parts = date_str.split(' ')
            if len(parts) >= 2 and ':' in parts[-1]:
                # Remove the time part
                date_str = ' '.join(parts[:-1])

        if date_format:
            try:
                return datetime.strptime(date_str, date_format).date()
            except ValueError:
                pass

        # Try common formats
        formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d',
            '%d %b %Y', '%d %B %Y',
            '%d/%m/%y', '%d-%m-%y',
            '%Y/%m/%d', '%m/%d/%Y'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        # Last resort - use dateutil
        try:
            return date_parser.parse(date_str, dayfirst=True).date()
        except:
            return None

    def parse_amount(self, value, is_debit: bool = False) -> float:
        """Parse amount from string, handling currency symbols."""
        if pd.isna(value):
            return 0.0

        if isinstance(value, (int, float)):
            amount = float(value)
        else:
            # Remove currency symbols and whitespace
            cleaned = str(value).replace('£', '').replace('$', '').replace('€', '')
            cleaned = cleaned.replace(',', '').strip()

            # Handle parentheses as negative
            if cleaned.startswith('(') and cleaned.endswith(')'):
                cleaned = '-' + cleaned[1:-1]

            try:
                amount = float(cleaned) if cleaned else 0.0
            except ValueError:
                return 0.0

        # Make debits negative
        if is_debit and amount > 0:
            amount = -amount

        return amount

    def generate_hash(self, date, description, amount) -> str:
        """Generate unique hash for transaction deduplication."""
        data = f"{date}|{description}|{amount}"
        return hashlib.sha256(data.encode()).hexdigest()

    def parse_transactions(self, column_mapping: dict = None) -> list[dict]:
        """Parse all transactions from the loaded file."""
        if self.df is None:
            self.load_file()

        if column_mapping is None:
            bank_format = self.detect_bank_format()
            column_mapping = self.get_column_mapping(bank_format)

        transactions = []
        date_format = column_mapping.get('date_format')

        for _, row in self.df.iterrows():
            # Parse date
            date_col = column_mapping.get('date_col')
            if not date_col or date_col not in row:
                continue

            date = self.parse_date(row[date_col], date_format)
            if date is None:
                continue

            # Parse description
            desc_col = column_mapping.get('description_col')
            description = str(row.get(desc_col, '')).strip() if desc_col else ''
            
            # Parse notes column (can be used as fallback or additional info)
            notes_col = column_mapping.get('notes_col')
            notes = str(row.get(notes_col, '')).strip() if notes_col else ''
            # Clean up 'nan' strings
            if notes.lower() == 'nan':
                notes = ''
            if description.lower() == 'nan':
                description = ''
            
            # Use notes as description fallback if description is empty
            if not description and notes:
                description = notes
            elif not description:
                continue
            
            # Parse bank-provided category
            cat_col = column_mapping.get('category_col')
            provided_category = str(row.get(cat_col, '')).strip() if cat_col else ''
            if provided_category.lower() == 'nan':
                provided_category = ''

            # Parse amount
            if 'amount_col' in column_mapping:
                amount = self.parse_amount(row.get(column_mapping['amount_col']))
            elif 'debit_col' in column_mapping and 'credit_col' in column_mapping:
                debit = self.parse_amount(row.get(column_mapping['debit_col']), is_debit=True)
                credit = self.parse_amount(row.get(column_mapping['credit_col']))
                amount = credit + debit  # debit is already negative
            else:
                continue

            # Skip zero amounts
            if amount == 0:
                continue

            # Parse balance
            balance = None
            if 'balance_col' in column_mapping:
                balance = self.parse_amount(row.get(column_mapping['balance_col']))

            # Generate hash for deduplication
            tx_hash = self.generate_hash(date, description, amount)

            transactions.append({
                'date': date,
                'description': description,
                'original_description': description,
                'amount': amount,
                'balance': balance,
                'hash': tx_hash,
                'notes': notes if notes and notes != description else '',
                'provided_category': provided_category
            })

        return transactions

    def get_columns(self) -> list[str]:
        """Get list of column names in the file."""
        if self.df is None:
            self.load_file()
        return list(self.df.columns)


def parse_statement(file_path: str, column_mapping: dict = None) -> list[dict]:
    """Convenience function to parse a statement file."""
    parser = StatementParser(file_path)
    return parser.parse_transactions(column_mapping)
