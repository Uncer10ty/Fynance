"""Statement import routes."""
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
from werkzeug.utils import secure_filename
from app import db
from app.models import Account, Transaction, Import
from app.services.parser import StatementParser
from app.services.categorizer import categorizer

imports_bp = Blueprint('imports', __name__)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@imports_bp.route('/')
def import_page():
    """Main import page."""
    accounts = Account.query.all()
    recent_imports = Import.query.order_by(Import.imported_at.desc()).limit(10).all()

    return render_template('imports/index.html',
                           accounts=accounts,
                           recent_imports=recent_imports)


@imports_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and preview columns."""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('imports.import_page'))

    file = request.files['file']
    account_id = request.form.get('account_id', type=int)

    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('imports.import_page'))

    if not allowed_file(file.filename):
        flash('Invalid file type. Please upload CSV or Excel files.', 'error')
        return redirect(url_for('imports.import_page'))

    if not account_id:
        flash('Please select an account', 'error')
        return redirect(url_for('imports.import_page'))

    # Save file
    filename = secure_filename(file.filename)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # Parse and detect format
    try:
        parser = StatementParser(file_path)
        parser.load_file()

        detected_format = parser.detect_bank_format()
        columns = parser.get_columns()
        column_mapping = parser.get_column_mapping(detected_format)

        # Preview first few rows
        preview_data = parser.df.head(5).to_dict('records')

        # Store in session for next step
        session['import_file'] = file_path
        session['import_account_id'] = account_id
        session['import_filename'] = filename

        account = Account.query.get(account_id)

        return render_template('imports/preview.html',
                               columns=columns,
                               column_mapping=column_mapping,
                               detected_format=detected_format,
                               preview_data=preview_data,
                               account=account,
                               filename=filename)

    except Exception as e:
        flash(f'Error reading file: {str(e)}', 'error')
        return redirect(url_for('imports.import_page'))


@imports_bp.route('/process', methods=['POST'])
def process_import():
    """Process the import with confirmed column mapping."""
    file_path = session.get('import_file')
    account_id = session.get('import_account_id')
    filename = session.get('import_filename')

    if not file_path or not account_id:
        flash('Import session expired. Please start again.', 'error')
        return redirect(url_for('imports.import_page'))

    # Get column mapping from form
    column_mapping = {
        'date_col': request.form.get('date_col'),
        'description_col': request.form.get('description_col'),
        'amount_col': request.form.get('amount_col') or None,
        'debit_col': request.form.get('debit_col') or None,
        'credit_col': request.form.get('credit_col') or None,
        'balance_col': request.form.get('balance_col') or None,
        'notes_col': request.form.get('notes_col') or None,
        'category_col': request.form.get('category_col') or None,
        'date_format': request.form.get('date_format') or None
    }
    
    # Get exclude patterns
    exclude_patterns_str = request.form.get('exclude_patterns', '').strip()
    exclude_patterns = [p.strip().lower() for p in exclude_patterns_str.split(',') if p.strip()]

    # Clean up empty values
    column_mapping = {k: v for k, v in column_mapping.items() if v}

    try:
        # Parse transactions
        parser = StatementParser(file_path)
        transactions_data = parser.parse_transactions(column_mapping)
        
        # Filter out excluded patterns
        if exclude_patterns:
            original_count = len(transactions_data)
            transactions_data = [
                tx for tx in transactions_data
                if not any(
                    pattern in tx['description'].lower() or 
                    pattern in tx.get('notes', '').lower() or
                    pattern in tx.get('provided_category', '').lower()
                    for pattern in exclude_patterns
                )
            ]
            excluded_count = original_count - len(transactions_data)
        else:
            excluded_count = 0

        if not transactions_data:
            flash('No transactions found in file (or all were excluded)', 'error')
            return redirect(url_for('imports.import_page'))

        # Create import record
        import_record = Import(
            account_id=account_id,
            filename=filename
        )
        db.session.add(import_record)
        db.session.flush()  # Get ID

        # Initialize categorizer rules if needed
        categorizer.initialize_default_rules()
        
        # Build a lookup for provided category names to our category IDs
        from app.models import Category
        category_lookup = {c.name.lower(): c.id for c in Category.query.all()}

        # Import transactions
        imported = 0
        duplicates = 0

        for tx_data in transactions_data:
            # Check for duplicate
            existing = Transaction.query.filter_by(hash=tx_data['hash']).first()
            if existing:
                duplicates += 1
                continue

            transaction = Transaction(
                account_id=account_id,
                date=tx_data['date'],
                description=tx_data['description'],
                original_description=tx_data['original_description'],
                amount=tx_data['amount'],
                balance=tx_data['balance'],
                hash=tx_data['hash'],
                notes=tx_data.get('notes', ''),
                import_id=import_record.id
            )
            
            # Try to match provided category first
            provided_cat = tx_data.get('provided_category', '').lower()
            if provided_cat and provided_cat in category_lookup:
                transaction.category_id = category_lookup[provided_cat]
                transaction.is_reviewed = False
            else:
                # Fall back to auto-categorize using rules
                categorizer.categorize_transaction(transaction)

            db.session.add(transaction)
            imported += 1

        # Update import record
        import_record.transaction_count = imported
        import_record.duplicates_skipped = duplicates

        db.session.commit()

        # Clean up session
        session.pop('import_file', None)
        session.pop('import_account_id', None)
        session.pop('import_filename', None)

        # Clean up file
        try:
            os.remove(file_path)
        except:
            pass

        # Build summary message
        msg_parts = [f'Imported {imported} transactions']
        if duplicates:
            msg_parts.append(f'{duplicates} duplicates skipped')
        if excluded_count:
            msg_parts.append(f'{excluded_count} excluded by filter')
        flash(', '.join(msg_parts), 'success')

        # Redirect to review if there are uncategorized transactions
        uncategorized = Transaction.query.filter(
            Transaction.import_id == import_record.id,
            Transaction.category_id == None
        ).count()

        if uncategorized > 0:
            flash(f'{uncategorized} transactions need categorization', 'info')
            return redirect(url_for('transactions.review'))

        return redirect(url_for('main.dashboard'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error importing transactions: {str(e)}', 'error')
        return redirect(url_for('imports.import_page'))


@imports_bp.route('/history')
def import_history():
    """View import history."""
    imports = Import.query.order_by(Import.imported_at.desc()).all()
    return render_template('imports/history.html', imports=imports)


@imports_bp.route('/<int:import_id>/delete', methods=['POST'])
def delete_import(import_id):
    """Delete an import and all its transactions."""
    import_record = Import.query.get_or_404(import_id)

    # Delete associated transactions
    Transaction.query.filter_by(import_id=import_id).delete()

    db.session.delete(import_record)
    db.session.commit()

    flash('Import deleted', 'success')
    return redirect(url_for('imports.import_history'))
