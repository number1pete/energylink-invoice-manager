# EnergyLink Scraper - Implementation Plan

## Context
We need a weekly Python script that scrapes the EnergyLink oil & gas royalty portal, navigating through invoices and well-level statement details, storing everything in SQLite. The script runs via Windows Task Scheduler. The user will handle MFA trust once manually; the script gracefully exits if MFA appears.

## Project Structure

```
Z:\Shares\Casey's Stuff\workbench\VSCode\EnergyLink\
├── EnergyLink-Site-Analysis.md          # (existing) reference doc
├── scraper.py                           # main entry point
├── config.py                            # configuration (credentials, paths, flags)
├── db.py                                # SQLite schema, connection, helpers
├── browser.py                           # Playwright login, MFA detection, navigation
├── parsers.py                           # page parsing logic (invoices, statements)
├── requirements.txt                     # Python dependencies
├── run_scraper.bat                      # Windows Task Scheduler launcher
├── .env                                 # credentials (not checked into source control)
└── data/
    ├── energylink.db                    # SQLite database (created at runtime)
    └── browser_state/                   # Playwright persistent context (cookies/session)
```

## Step 1: Environment Setup
- Create venv at `C:\Users\cbroo\venv\energynet`
- Install: `playwright`, `python-dotenv`, plus Chromium browser via `playwright install chromium`
- Create `requirements.txt`

## Step 2: config.py + .env

**.env file** (not checked into source control):
```
ENERGYLINK_USERNAME=cbbroome@gmail.com
ENERGYLINK_PASSWORD=cmd5RWD!quw9mwv0qnb
```

**config.py** loads from .env via `python-dotenv`:
- ENERGYLINK_URL (hardcoded)
- USERNAME / PASSWORD (from .env)
- DB_PATH (points to data/energylink.db)
- DEBUG flag (True = first invoice only)
- HEADLESS flag (True for scheduler, False for testing)
- BROWSER_STATE_PATH (Playwright persistent context dir for cookies/session)
- SCRAPE_TIMEOUT values

## Step 3: SQLite Schema (db.py)

### Table: `scrape_runs`
Tracks each execution of the script.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| started_at | TEXT | ISO timestamp |
| finished_at | TEXT | ISO timestamp (null if crashed) |
| status | TEXT | 'running', 'success', 'failure', 'mfa_required' |
| invoices_processed | INTEGER | Count of invoices scraped this run |
| invoices_skipped | INTEGER | Count already in DB |
| error_message | TEXT | Error details if failed |

### Table: `scrape_logs`
Detailed log entries per run.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| run_id | INTEGER FK | References scrape_runs.id |
| timestamp | TEXT | ISO timestamp |
| level | TEXT | 'INFO', 'WARNING', 'ERROR' |
| message | TEXT | Log message |

### Table: `invoices`
One row per operator check/invoice.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| invoice_id | INTEGER UNIQUE | EnergyLink InvoiceId (from URL) |
| doc_type | TEXT | e.g. 'REVENUE' |
| operator | TEXT | Operator name |
| owner_number | TEXT | Owner # |
| check_number | TEXT | Invoice/Check number |
| invoice_date | TEXT | Invoice/Check date |
| op_acct_month | TEXT | Operator accounting month |
| received_date | TEXT | Date received |
| status | TEXT | 'New', 'Viewed' |
| total_revenue | REAL | Revenue subtotal |
| total_tax | REAL | Tax subtotal |
| total_deductions | REAL | Deductions subtotal |
| total_amount | REAL | Net total |
| scraped_at | TEXT | When we scraped this |
| run_id | INTEGER FK | Which run scraped it |

### Table: `properties`
One row per well/property within an invoice.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| invoice_id | INTEGER FK | References invoices.invoice_id |
| statement_id | INTEGER UNIQUE | EnergyLink StatementId (from URL) |
| cost_center | TEXT | Cost center code |
| description | TEXT | Well/property name |
| state | TEXT | State abbreviation |
| county | TEXT | County name |
| owner_share_revenue | REAL | Revenue for this property |
| tax | REAL | Tax for this property |
| deductions | REAL | Deductions for this property |
| total | REAL | Net total for this property |
| scraped_at | TEXT | When we scraped this |

### Table: `statement_details`
One row per line item on a statement.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| statement_id | INTEGER FK | References properties.statement_id |
| product_category | TEXT | e.g. 'PLANT PRODUCTS', 'RESIDUE GAS', 'OIL' |
| code | TEXT | e.g. '400.RI', '204.01' |
| type_description | TEXT | e.g. 'ROYALTY INTEREST', 'COMPRESSION' |
| production_date | TEXT | e.g. 'Nov 25' |
| btu | REAL | BTU factor (nullable) |
| property_volume | REAL | Total property volume (nullable) |
| property_price | REAL | Unit price (nullable) |
| property_value | REAL | Total property value (nullable) |
| owner_pct | REAL | Owner percentage |
| distribution_pct | REAL | Distribution percentage (nullable) |
| owner_volume | REAL | Owner's volume share (nullable) |
| owner_value | REAL | Owner's dollar value |

## Step 4: browser.py - Browser Automation

### Login flow:
1. Launch Playwright with **persistent context** (saves cookies to `data/browser_state/`) so MFA "trust this device" persists between runs
2. Navigate to https://app.energylink.com/
3. If already logged in (redirects to dashboard), continue
4. If on login page, fill email/password, click Sign In
5. If MFA page detected (URL contains `mfa-sms-challenge` or page has "Verify Your Identity"): log error, set run status to `mfa_required`, exit gracefully
6. Wait for dashboard to load

### Invoice list scraping:
1. Navigate to `Dashboard#invoices`
2. Wait for AG Grid to render
3. For each page of the grid:
   - Extract all invoice rows: parse InvoiceId from the View/Total link href, plus all visible cell data (doc type, operator, owner#, check#, dates, status, total)
   - Check each invoice_id against the `invoices` table - skip if already exists
   - Click "Next page" button, wait for grid to update
   - If DEBUG, stop after collecting the first unprocessed invoice
4. Return list of invoice IDs to process

### Invoice Summary scraping:
1. Navigate to `/Invoice/InvoiceSummary.aspx?InvoiceId={id}&Context=Inbound`
2. Parse header: check number, revenue, tax, deductions, total
3. Parse properties table: for each row, extract Cost Center, Description, State, County, Revenue, Tax, Deductions, Total, and the StatementId from the View link href
4. Insert invoice record + all property records into DB

### Statement Detail scraping:
1. For each property/StatementId from the invoice:
   - Navigate to `/Statement/StatementSummary.aspx?StatementId={id}&Context=Inbound`
   - Parse the detail table: identify product category grouping rows (PLANT PRODUCTS, RESIDUE GAS, etc.), then parse each detail row underneath
   - Insert all statement_detail records into DB
2. Rate limiting: small delay between page loads to be respectful

## Step 5: parsers.py - HTML Parsing

Since Invoice Summary and Statement Summary are ASP.NET table-based pages, we'll parse them using Playwright's DOM querying:
- **Invoice list (AG Grid)**: Use `page.locator()` to find grid rows and extract cell text + link hrefs
- **Invoice Summary**: Query the properties table rows, extract cell text and StatementId from hrefs
- **Statement Summary**: Query detail table rows, detect category headers vs data rows, extract all fields

## Step 6: scraper.py - Main Orchestrator

```
def main():
    1. Parse command-line args (--debug, --headless)
    2. Initialize DB (create tables if not exist)
    3. Create scrape_run record (status='running')
    4. Launch browser, attempt login
    5. If MFA hit -> log, update run status, exit
    6. Scrape invoice list -> get unprocessed invoice IDs
    7. For each invoice ID:
       a. Scrape invoice summary page
       b. Insert invoice + properties into DB
       c. For each property/statement:
          - Scrape statement detail page
          - Insert statement details into DB
       d. Log progress
    8. Update scrape_run record (status='success', counts)
    9. Close browser
    10. On any exception: log error, update run to 'failure', close browser
```

## Step 7: run_scraper.bat

```bat
@echo off
call C:\Users\cbroo\venv\energynet\Scripts\activate.bat
python "Z:\Shares\Casey's Stuff\workbench\VSCode\EnergyLink\scraper.py" --headless
```

## Step 8: Verification / Testing

1. Run with `--debug` flag (processes only first invoice)
2. Verify SQLite has correct data in all 5 tables
3. Run again with `--debug` to verify it **skips** the already-processed invoice
4. Check `scrape_runs` and `scrape_logs` tables for proper tracking
5. Test MFA detection by clearing browser state
6. Full run without `--debug` to backfill all invoices

## Implementation Order
1. Create venv + install dependencies
2. Write .env + config.py
3. Write db.py (schema + helpers)
4. Write browser.py (login + MFA detection)
5. Write parsers.py (page parsing)
6. Write scraper.py (main orchestrator)
7. Write run_scraper.bat
8. Test with --debug
