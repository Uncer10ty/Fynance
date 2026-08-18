# Fynance

> A lightweight personal finance web app to import, categorize, analyze, and review transactions.

## Key Features
- Import CSV transaction exports (e.g., Trading212) and preview before importing
- Rule-based categorization and automatic suggestions
- Transaction review, manual categorization, and monthly views
- Accounts and category management

## Tech stack
- Python 3.8+ (tested with 3.8/3.9/3.10)
- Flask for the web app
- Dependencies listed in [requirements.txt](requirements.txt)

## Prerequisites
- Python 3.8 or newer
- A virtual environment tool (`venv`, `virtualenv`, or similar)

## Quickstart
1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows PowerShell: .\\.venv\\Scripts\\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure (optional): edit `config.py` for DB, secret keys, or other settings.

4. Run the application locally:

```bash
python run.py
```

Open http://127.0.0.1:5000/ in your browser.

## Project layout

- [run.py](run.py) — application entry point
- [config.py](config.py) — runtime configuration
- [requirements.txt](requirements.txt) — Python dependencies
- [app/](app/) — Flask application package
  - [app/__init__.py](app/__init__.py) — app factory and initialization
  - [app/models.py](app/models.py) — database models (transactions, accounts, categories, rules)
  - [app/routes/](app/routes/) — HTTP routes and view handlers
    - [app/routes/main.py](app/routes/main.py) — dashboard and main pages
    - [app/routes/accounts.py](app/routes/accounts.py) — account CRUD views
    - [app/routes/categories.py](app/routes/categories.py) — categories and rules UI
    - [app/routes/transactions.py](app/routes/transactions.py) — transaction listing and review
    - [app/routes/imports.py](app/routes/imports.py) — import flow (preview & history)
  - [app/services/](app/services/) — core backend logic
    - [app/services/parser.py](app/services/parser.py) — CSV parsing and normalization
    - [app/services/categorizer.py](app/services/categorizer.py) — rule matching and suggestions
    - [app/services/analyzer.py](app/services/analyzer.py) — reporting and summaries
  - [app/templates/](app/templates/) — Jinja2 HTML templates

- [data/](data/) — persistent data (if applicable)
- [uploads/](uploads/) — sample uploaded CSVs (e.g., Trading212_Sep-Dec.csv)

## Import workflow
1. Navigate to the Imports section in the UI.
2. Upload a CSV (put files under `uploads/` for manual testing).
3. Use the preview page to confirm parsed rows: see [app/routes/imports.py](app/routes/imports.py).
4. Accept to import; transactions will be created and categorized according to rules.

## Categorization and Rules
- Rules are managed via the Categories UI ([app/routes/categories.py](app/routes/categories.py)).
- The `categorizer` service applies rule patterns to transaction descriptions to auto-assign categories.

## Templates and UI
- Base layout: [app/templates/base.html](app/templates/base.html)
- Dashboard: [app/templates/dashboard.html](app/templates/dashboard.html)
- Accounts, Categories, Imports, Transactions subfolders contain respective views.

## Development notes
- Add or modify parsing logic in `app/services/parser.py` when supporting new CSV formats.
- Keep business logic in `app/services/` and keep routes thin.

## Testing
There are no automated tests included yet. To test manually:

```bash
# Create venv, install deps, run the app, then exercise routes via browser
python run.py
```

## Troubleshooting
- If the server fails to start, check `config.py` for invalid settings.
- Ensure required packages are installed from `requirements.txt`.

## Next improvements (ideas)
- Add unit/integration tests
- Persist data with a database and migrations
- Dockerfile + docker-compose for reproducible local development
- Add user authentication and multi-user support
