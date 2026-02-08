"""Page parsing logic for EnergyLink scraper.

Extracts structured data from the Invoices/Checks grid, Invoice Summary,
and Statement Summary pages using Playwright DOM queries.
"""

import re
import time
from playwright.sync_api import Page

import config


def _parse_money(text: str) -> float | None:
    """Parse a money string like '$5,726.28' or '(155.13)' into a float."""
    if not text or not text.strip():
        return None
    text = text.strip().replace("$", "").replace(",", "")
    # Handle parenthesized negatives: (155.13) -> -155.13
    match = re.match(r"^\((.+)\)$", text)
    if match:
        return -float(match.group(1))
    try:
        return float(text)
    except ValueError:
        return None


def _parse_pct(text: str) -> float | None:
    """Parse a percentage string like '6.25000000 %' into a float."""
    if not text or not text.strip():
        return None
    text = text.strip().replace("%", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def _clean(text: str) -> str:
    """Clean whitespace from extracted text."""
    if not text:
        return ""
    return text.strip()


def _extract_id_from_href(href: str, param: str) -> int | None:
    """Extract an integer ID from a URL parameter."""
    match = re.search(rf"{param}=(\d+)", href)
    return int(match.group(1)) if match else None


# --- Invoice List (AG Grid on Invoices/Checks tab) ---

def parse_invoice_list(page: Page) -> list[dict]:
    """Parse all invoices from the AG Grid on the Invoices/Checks tab.

    The AG Grid renders as divs with .ag-row / .ag-cell classes, and also
    uses ARIA roles (role='row', role='gridcell'). The InvoiceId comes from
    links to InvoiceSummary.aspx in the Total column.

    Returns a list of dicts.
    """
    all_invoices = []

    # There are two AG Grids on the page (Dashboard + Invoices/Checks).
    # The Invoices grid rows have 12 cells including col-id='status'.
    # We identify it by finding .ag-center-cols-container that has
    # rows with the 'status' column cell.
    containers = page.locator(".ag-center-cols-container").all()
    invoices_container = None
    for c in containers:
        if c.locator(".ag-row .ag-cell[col-id='status']").count() > 0:
            invoices_container = c
            break

    if not invoices_container:
        return all_invoices

    # Wait for rows to be present
    try:
        invoices_container.locator(".ag-row").first.wait_for(
            state="visible", timeout=config.GRID_TIMEOUT
        )
    except Exception:
        return all_invoices

    # The pagination controls are siblings of the grid, find them at page level
    while True:
        invoices_on_page = _parse_grid_page(invoices_container)
        all_invoices.extend(invoices_on_page)

        if not _go_to_next_grid_page(page):
            break

    return all_invoices


def _parse_grid_page(container) -> list[dict]:
    """Parse invoice rows from the current AG Grid page."""
    invoices = []

    # Target .ag-row elements inside the Invoices container
    rows = container.locator(".ag-row").all()

    for row in rows:
        try:
            invoice = _parse_grid_row(row)
            if invoice and invoice.get("invoice_id"):
                invoices.append(invoice)
        except Exception:
            continue

    return invoices


def _parse_grid_row(row) -> dict | None:
    """Parse a single AG Grid row into an invoice dict.

    Uses col-id attributes for reliable cell identification:
      ag-Grid-SelectionColumn, dataSource, operatorName, ownerNumber,
      invoice, opAccountingMonth, status, original, view, pdf, excel, more

    The row-id attribute contains the InvoiceId directly.
    """
    # Get InvoiceId from the row-id attribute
    row_id = row.get_attribute("row-id")
    if not row_id or not row_id.isdigit():
        return None
    invoice_id = int(row_id)

    def col(col_id):
        cell = row.locator(f".ag-cell[col-id='{col_id}']")
        if cell.count() > 0:
            return _clean(cell.first.inner_text())
        return ""

    # Invoice/Check column: "110355\n2026-01-30"
    invoice_text = col("invoice")
    check_lines = invoice_text.split("\n")
    check_number = check_lines[0].strip() if check_lines else ""
    invoice_date = check_lines[1].strip() if len(check_lines) > 1 else ""

    # Op Acct Month column: "2026-01-31\n2026-01-30"
    op_text = col("opAccountingMonth")
    op_lines = op_text.split("\n")
    op_acct_month = op_lines[0].strip() if op_lines else ""
    received_date = op_lines[1].strip() if len(op_lines) > 1 else ""

    return {
        "invoice_id": invoice_id,
        "doc_type": col("dataSource"),
        "operator": col("operatorName"),
        "owner_number": col("ownerNumber"),
        "check_number": check_number,
        "invoice_date": invoice_date,
        "op_acct_month": op_acct_month,
        "received_date": received_date,
        "status": col("status"),
        "total_amount": _parse_money(col("original")),
    }


def _go_to_next_grid_page(page) -> bool:
    """Click the next page button in AG Grid pagination. Returns False if on last page."""
    try:
        # The pagination uses a custom .pagination-container with:
        #   - .textbox-pagenumber input for current page
        #   - .pagination-btn buttons (first/prev are disabled on page 1)
        #   - Text like "1 to 20 of 105" and "Page [input] of 6"
        # There are two pagination containers (Dashboard + Invoices).
        # Target the visible one.
        pagination = page.locator(".pagination-container:visible")
        if pagination.count() == 0:
            return False

        page_input = pagination.locator(".textbox-pagenumber").first
        if page_input.count() == 0:
            return False

        current_page = int(page_input.input_value())

        # Get total pages from "of N" text in the pagination container
        pagination_text = pagination.first.inner_text()
        match = re.search(r"of\s+(\d+)\s*$", pagination_text)
        if not match:
            return False
        total_pages = int(match.group(1))

        if current_page >= total_pages:
            return False

        # Navigate by filling the page input with the next page number
        next_page = current_page + 1
        page_input.click()
        page_input.fill(str(next_page))
        page_input.press("Enter")

        time.sleep(2)
        return True

    except Exception:
        return False


# --- Invoice Summary Page ---

def parse_invoice_summary(page: Page, invoice_id: int) -> dict:
    """Parse the Invoice Summary page.

    Returns a dict with:
      invoice_id, check_number, total_revenue, total_tax,
      total_deductions, total_amount, properties (list of dicts)
    """
    result = {"invoice_id": invoice_id, "properties": []}

    # Parse financial summary from the labeled table
    # The financials are in a table with rows like:
    #   "Check Number" | "110355"
    #   "Revenue"      | "6,776.94"
    result.update(_parse_invoice_financials(page))

    # Parse properties table
    result["properties"] = _parse_properties_table(page, invoice_id)

    return result


def _parse_invoice_financials(page: Page) -> dict:
    """Extract check number, revenue, tax, deductions, total from invoice summary."""
    financials = {}

    # Find all table rows and look for labeled value pairs
    rows = page.locator("tr").all()
    for row in rows:
        cells = row.locator("td").all()
        if len(cells) == 2:
            label = _clean(cells[0].inner_text())
            value = _clean(cells[1].inner_text())

            if label == "Check Number":
                financials["check_number"] = value
            elif label == "Revenue":
                financials["total_revenue"] = _parse_money(value)
            elif label == "Tax":
                financials["total_tax"] = _parse_money(value)
            elif label == "Deductions":
                financials["total_deductions"] = _parse_money(value)
            elif label == "Total":
                financials["total_amount"] = _parse_money(value)

    return financials


def _parse_properties_table(page: Page, invoice_id: int) -> list[dict]:
    """Parse the properties/wells table from an Invoice Summary page."""
    properties = []

    # Property rows contain links to StatementSummary
    rows = page.locator("tr:has(a[href*='StatementId'])").all()

    for row in rows:
        try:
            prop = _parse_property_row(row, invoice_id)
            if prop and prop.get("statement_id"):
                properties.append(prop)
        except Exception:
            continue

    return properties


def _parse_property_row(row, invoice_id: int) -> dict | None:
    """Parse a single property row from the invoice summary.

    Row structure (td cells):
      0: View link (with StatementId)
      1: Cost Center (e.g., "204381363")
      2: Description (e.g., "ADAMS, T. C. NCT-1 C 1")
      3: State (e.g., "TX")
      4: County (e.g., "PANOLA")
      5: Owner Share Revenue (e.g., "651.88")
      6: Tax (e.g., "(31.98)")
      7: Deductions (e.g., "(127.38)")
      8: Total (e.g., "492.52")
    """
    # Get StatementId from link
    statement_id = None
    link = row.locator("a[href*='StatementId']").first
    href = link.get_attribute("href") or ""
    statement_id = _extract_id_from_href(href, "StatementId")

    if not statement_id:
        return None

    cells = row.locator("td").all()
    cell_texts = [_clean(c.inner_text()) for c in cells]

    # Find the cost center column (9+ digit numeric string)
    cost_center_idx = None
    for i, txt in enumerate(cell_texts):
        if re.match(r"^\d{6,}$", txt.strip()):
            cost_center_idx = i
            break

    if cost_center_idx is None:
        return None

    def get(offset):
        idx = cost_center_idx + offset
        return cell_texts[idx] if idx < len(cell_texts) else ""

    return {
        "invoice_id": invoice_id,
        "statement_id": statement_id,
        "cost_center": get(0),
        "description": get(1),
        "state": get(2),
        "county": get(3),
        "owner_share_revenue": _parse_money(get(4)),
        "tax": _parse_money(get(5)),
        "deductions": _parse_money(get(6)),
        "total": _parse_money(get(7)),
    }


# --- Statement Summary Page ---

def parse_statement_details(page: Page, statement_id: int) -> list[dict]:
    """Parse line items from a Statement Summary page.

    The detail table has:
    - Header row: Code, Type Desc, Production Date, BTU, Volume, Price, Value,
                   Owner %, Distribution %, Volume, Value
    - Category rows: single cell with text like "PLANT PRODUCTS", "RESIDUE GAS"
    - Data rows: 12 cells (code, type, date, btu, vol, price, val, owner%, dist%, vol, val, empty)
    - Subtotal rows: "Total for PLANT PRODUCTS", "Total for RESIDUE GAS", "Total for Statement"
    """
    details = []
    current_category = ""

    # The detail table has rows with product codes (e.g., "400.RI", "GDP.RI").
    # There may be two tables with "Code" headers (frozen header + data table).
    # We want the one that contains data rows with category headers.
    # Different operators use different category names:
    #   TGNR: "PLANT PRODUCTS", "RESIDUE GAS", "OIL"
    #   Sheridan/EXCO: "GAS DELIVERED TO PLANT", "GAS RESIDUE", "NGL"
    # Find the data table by looking for any of these category names.
    _CATEGORY_SELECTORS = [
        "PLANT PRODUCTS", "RESIDUE GAS", "OIL",
        "GAS DELIVERED TO PLANT", "GAS RESIDUE", "NGL",
        "GAS", "CONDENSATE", "CRUDE OIL",
    ]
    selector = ", ".join(f"table:has(td:text-is('{cat}'))" for cat in _CATEGORY_SELECTORS)
    detail_table = page.locator(selector).last

    try:
        detail_table.wait_for(state="visible", timeout=config.LOAD_TIMEOUT)
    except Exception:
        # Fallback: find tables with "Code" header and data rows
        detail_table = None
        all_tables = page.locator("table").all()
        for t in reversed(all_tables):
            rows_in_table = t.locator("tr").count()
            if rows_in_table > 5:
                text = t.inner_text()
                if "Code" in text and "Type Desc" in text and "ROYALTY" in text:
                    detail_table = t
                    break
        if detail_table is None:
            return details

    rows = detail_table.locator("tr").all()

    for row in rows:
        cells = row.locator("td").all()
        if not cells:
            continue  # header row (th cells)

        row_text = _clean(row.inner_text())
        cell_count = len(cells)

        # Skip header-like rows
        if "Code" in row_text and "Type Desc" in row_text:
            continue

        # Skip "Show Subtext" / "Details X - Y" rows
        if "Show Subtext" in row_text or "Details" in row_text:
            continue

        # Category header: single cell (or few cells) with all-caps text
        if cell_count == 1:
            cat_text = _clean(cells[0].inner_text())
            if cat_text and cat_text.isupper() and not cat_text.startswith("Total"):
                current_category = cat_text
            continue

        # Subtotal/total rows: starts with "Total for ..."
        first_cell_text = _clean(cells[0].inner_text())
        if first_cell_text.startswith("Total for") or first_cell_text == "Total":
            continue

        # Data rows have 12 cells:
        # 0:Code, 1:Type Desc, 2:Prod Date, 3:BTU, 4:Prop Volume,
        # 5:Prop Price, 6:Prop Value, 7:Owner%, 8:Dist%, 9:Owner Vol,
        # 10:Owner Value, 11:(empty)
        if cell_count < 11:
            continue

        code = first_cell_text
        # Codes can be numeric (400.RI, 204.01) or alpha (GDP.RI, GSAR.GTHD, N.RI)
        if not code or not re.match(r"^\w+\.\w+$", code):
            continue

        cell_texts = [_clean(c.inner_text()) for c in cells]

        details.append({
            "statement_id": statement_id,
            "product_category": current_category,
            "code": code,
            "type_description": cell_texts[1],
            "production_date": cell_texts[2],
            "btu": _parse_money(cell_texts[3]),
            "property_volume": _parse_money(cell_texts[4]),
            "property_price": _parse_money(cell_texts[5]),
            "property_value": _parse_money(cell_texts[6]),
            "owner_pct": _parse_pct(cell_texts[7]),
            "distribution_pct": _parse_pct(cell_texts[8]),
            "owner_volume": _parse_money(cell_texts[9]),
            "owner_value": _parse_money(cell_texts[10]),
        })

    return details
