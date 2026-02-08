# EnergyLink Web Viewer - Implementation Plan

## Context
The EnergyLink scraper is complete with 105 invoices, 629 properties, and 4,767 statement detail line items in SQLite. The user wants a Flask SPA to visualize this data with interactive charts, filterable tables, CSV export, and an invoice generator with print capability. The app lives in `EnergyLink-Web-Viewer/` as a subdirectory of the existing project.

## Project Structure

```
EnergyLink-Web-Viewer/
├── app.py                          # Flask app factory + entry point
├── requirements.txt                # Flask dependencies
├── run_viewer.bat                  # Launcher script
├── db_queries.py                   # SQL query layer (all DB access)
├── blueprints/
│   ├── __init__.py
│   ├── dashboard.py                # /api/dashboard/* endpoints
│   └── invoices.py                 # /api/invoices/* endpoints
├── static/
│   ├── css/
│   │   └── style.css               # Custom styles + print CSS
│   └── js/
│       ├── app.js                  # SPA tab routing, filter init
│       ├── charts.js               # Plotly chart rendering
│       ├── tables.js               # DataTables init + CSV export
│       └── invoice.js              # Invoice generator logic
└── templates/
    └── index.html                  # Single-page shell (both tabs)
```

## Database Access (db_queries.py)

Reads from the existing `../data/energylink.db` (read-only). All queries in one module.

### Key queries:
1. **Filter options**: distinct operators, properties, product categories, date range
2. **Monthly rollup**: GROUP BY `production_date`, with calculated $/MCF columns
3. **Raw detail data**: JOINed statement_details + properties + invoices, with $/MCF columns
4. **Invoice list**: all invoices for the invoice selector
5. **Invoice detail**: single invoice with its properties and statement details

### $/MCF Calculation Logic
For each row in statement_details:
- **Revenue $/MCF** = `owner_value / owner_volume` (for revenue lines like ROYALTY INTEREST)
- **Expense $/MCF** (compression, gathering, etc.) = `ABS(owner_value) / revenue_volume` where `revenue_volume` is the total ROYALTY INTEREST volume for the same statement

For monthly rollup, aggregate then divide:
- `SUM(owner_value) / SUM(owner_volume)` for revenue
- `SUM(ABS(expense_value)) / SUM(revenue_volume)` for each expense type

Revenue lines identified by: `type_description = 'ROYALTY INTEREST'`
Expense lines: everything else (COMPRESSION, GATHERING, TREATING, TRANSPORTATION, etc.)

## Step 1: Flask App Shell

**`app.py`** - Application factory pattern:
- Create Flask app, register blueprints
- SQLite connection via `g` object (connection-per-request)
- DB path: `../data/energylink.db` relative to app directory
- Serve `index.html` at `/`
- Debug mode via `--debug` flag

**`requirements.txt`**: `flask`

**`run_viewer.bat`**: Activates venv, runs `python app.py`

## Step 2: SQL Query Layer (db_queries.py)

All functions take a `sqlite3.Connection` and optional filter params dict:
- `operators` (list), `date_start`, `date_end`, `properties` (list), `categories` (list)

Functions:
- `get_filter_options(conn)` -> dict of distinct values for each filter
- `get_monthly_rollup(conn, filters)` -> list of dicts grouped by month
- `get_raw_details(conn, filters)` -> list of dicts (full JOINed data)
- `get_invoice_list(conn)` -> list of invoice summary dicts
- `get_invoice_detail(conn, invoice_id)` -> invoice + properties + details

The monthly rollup query (core logic):
```sql
-- Step 1: Get revenue volume per statement (denominator for expense $/MCF)
WITH rev_volume AS (
    SELECT statement_id, SUM(owner_volume) as vol
    FROM statement_details
    WHERE type_description = 'ROYALTY INTEREST'
    GROUP BY statement_id
)
-- Step 2: Join and aggregate by month
SELECT
    sd.production_date,
    SUM(CASE WHEN sd.type_description = 'ROYALTY INTEREST' THEN sd.owner_value ELSE 0 END) as revenue,
    SUM(CASE WHEN sd.type_description = 'ROYALTY INTEREST' THEN sd.owner_volume ELSE 0 END) as volume,
    -- Revenue $/MCF
    SUM(CASE WHEN sd.type_description = 'ROYALTY INTEREST' THEN sd.owner_value ELSE 0 END)
      / NULLIF(SUM(CASE WHEN sd.type_description = 'ROYALTY INTEREST' THEN sd.owner_volume ELSE 0 END), 0) as revenue_per_mcf,
    -- Price (avg property_price for revenue lines)
    AVG(CASE WHEN sd.type_description = 'ROYALTY INTEREST' THEN sd.property_price END) as avg_price,
    -- Each expense type $/MCF
    SUM(CASE WHEN sd.type_description = 'COMPRESSION' THEN ABS(sd.owner_value) ELSE 0 END)
      / NULLIF(SUM(CASE WHEN sd.type_description = 'ROYALTY INTEREST' THEN sd.owner_volume ELSE 0 END), 0) as compression_per_mcf,
    SUM(CASE WHEN sd.type_description = 'GATHERING' THEN ABS(sd.owner_value) ELSE 0 END)
      / NULLIF(...) as gathering_per_mcf,
    -- ... similar for TREATING, TRANSPORTATION, MARKETING, etc.
    -- Total expenses $/MCF (sum of all expense $/MCF)
FROM statement_details sd
JOIN properties p ON sd.statement_id = p.statement_id
JOIN invoices i ON p.invoice_id = i.invoice_id
WHERE [dynamic filters]
GROUP BY sd.production_date
ORDER BY sd.production_date
```

Dynamic WHERE clause built from filter params using parameterized queries.

## Step 3: API Blueprints

**`blueprints/dashboard.py`**:
- `GET /api/dashboard/filters` -> filter options
- `GET /api/dashboard/monthly?operators=...&date_start=...&date_end=...&properties=...&categories=...` -> monthly rollup
- `GET /api/dashboard/details?...` -> raw detail rows

**`blueprints/invoices.py`**:
- `GET /api/invoices` -> invoice list (id, operator, check_number, date, total)
- `GET /api/invoices/<invoice_id>` -> full invoice with properties and statement details

All endpoints return JSON. Query params parsed in the blueprint, passed to db_queries functions.

## Step 4: Frontend - HTML Shell (templates/index.html)

Single page with Bootstrap 5 (CDN). Two tabs:

**Tab 1 - Dashboard**:
- Left sidebar (col-3): filter panel with Choices.js multi-selects for Operator, Property, Category + date range inputs + Apply button
- Main area (col-9):
  - Top row: two Plotly charts side by side (col-6 each)
  - Bottom row: two DataTables (monthly rollup + raw data), each with CSV export button

**Tab 2 - Invoice Generator**:
- Dropdown to select invoice (Choices.js searchable)
- Rendered invoice below with print-friendly layout
- Print button triggers `window.print()`

CDN libraries:
- Bootstrap 5.3 (CSS + JS)
- Plotly.js (charts)
- DataTables 2.x + Buttons extension (tables + CSV)
- Choices.js (searchable multi-select dropdowns)

## Step 5: Frontend - JavaScript

**`static/js/app.js`**:
- Tab switching via Bootstrap nav
- On page load: fetch `/api/dashboard/filters`, populate filter dropdowns
- Apply button: fetch monthly + details endpoints, pass to charts.js + tables.js
- Auto-apply on first load with no filters (show all data)

**`static/js/charts.js`**:
- `renderLineChart(data, config)`: Plotly line chart in `#line-chart` div
  - Default traces: Revenue $/MCF (left Y), Price (right Y), Total Expenses $/MCF (left Y)
  - Dropdown checkboxes above chart to toggle traces on/off
  - Trace options: Revenue $/MCF, Price, Compression $/MCF, Gathering $/MCF, Treating $/MCF, Transportation $/MCF, Total Expenses $/MCF, Volume
  - Dual Y-axis toggle per series
- `renderComboChart(data, config)`: Plotly bar+line combo in `#combo-chart` div
  - Default: Revenue as bars (left Y), Natural Gas Price as line (right Y)
  - Dropdowns to select bar series and line series

**`static/js/tables.js`**:
- `renderRollupTable(data)`: DataTable in `#rollup-table`
  - Columns: Month, Revenue, Volume (MCF), Revenue $/MCF, Price, Compression $/MCF, Gathering $/MCF, ..., Total Expenses $/MCF, Net $/MCF
  - CSV export button
- `renderRawTable(data)`: DataTable in `#raw-table`
  - Columns: Month, Operator, Property, Category, Code, Type, Volume, Price, Value, Owner%, Owner Volume, Owner Value
  - CSV export button

**`static/js/invoice.js`**:
- Fetch `/api/invoices` to populate selector
- On select: fetch `/api/invoices/<id>`, render invoice HTML
- Invoice layout: header (operator, check#, date), financial summary, properties table with nested statement details
- Print button: `window.print()` with `@media print` CSS

## Step 6: Styling (static/css/style.css)

- Filter sidebar: fixed height, scrollable, compact spacing
- Charts: responsive width
- Tables: Bootstrap-styled DataTables
- `@media print`: hide sidebar/nav/filters, show invoice full-width

## Files to Create (13 files)

1. `EnergyLink-Web-Viewer/app.py`
2. `EnergyLink-Web-Viewer/requirements.txt`
3. `EnergyLink-Web-Viewer/run_viewer.bat`
4. `EnergyLink-Web-Viewer/db_queries.py`
5. `EnergyLink-Web-Viewer/blueprints/__init__.py`
6. `EnergyLink-Web-Viewer/blueprints/dashboard.py`
7. `EnergyLink-Web-Viewer/blueprints/invoices.py`
8. `EnergyLink-Web-Viewer/templates/index.html`
9. `EnergyLink-Web-Viewer/static/css/style.css`
10. `EnergyLink-Web-Viewer/static/js/app.js`
11. `EnergyLink-Web-Viewer/static/js/charts.js`
12. `EnergyLink-Web-Viewer/static/js/tables.js`
13. `EnergyLink-Web-Viewer/static/js/invoice.js`

## Existing Files Referenced (read-only)
- `data/energylink.db` - SQLite database (105 invoices, 629 properties, 4,767 statement details)
- `db.py` - existing schema reference (tables: invoices, properties, statement_details)
- `config.py` - DB_PATH reference

## Implementation Order
1. Create directory structure + `requirements.txt` + `run_viewer.bat`
2. `app.py` (Flask shell + DB connection)
3. `db_queries.py` (all SQL queries with $/MCF calculations)
4. `blueprints/dashboard.py` + `blueprints/invoices.py` (API endpoints)
5. `templates/index.html` (HTML shell with CDN imports)
6. `static/js/app.js` (SPA routing + filters)
7. `static/js/charts.js` (Plotly charts)
8. `static/js/tables.js` (DataTables + CSV)
9. `static/js/invoice.js` (invoice generator)
10. `static/css/style.css` (styling + print)

## Verification
1. Install Flask: `pip install flask` in the energynet venv
2. Run `python app.py --debug` from `EnergyLink-Web-Viewer/`
3. Open http://localhost:5000 in browser
4. Verify filter panel loads with operators/properties/categories from DB
5. Verify both charts render with default series
6. Verify both tables populate with data and CSV export works
7. Switch to Invoice tab, select an invoice, verify it renders
8. Test print preview (Ctrl+P) on an invoice
