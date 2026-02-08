"""SQL query layer for EnergyLink Web Viewer. All DB access goes through here."""

import sqlite3


_MONTH_NUM = {
    'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
    'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
    'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
}

# SQL expression to convert "Mon YY" to "20YY-MM" for chronological comparison
_DATE_SORT_EXPR = (
    "('20' || SUBSTR(sd.production_date, 5, 2) || '-' || "
    "CASE SUBSTR(sd.production_date, 1, 3) "
    "WHEN 'Jan' THEN '01' WHEN 'Feb' THEN '02' WHEN 'Mar' THEN '03' "
    "WHEN 'Apr' THEN '04' WHEN 'May' THEN '05' WHEN 'Jun' THEN '06' "
    "WHEN 'Jul' THEN '07' WHEN 'Aug' THEN '08' WHEN 'Sep' THEN '09' "
    "WHEN 'Oct' THEN '10' WHEN 'Nov' THEN '11' WHEN 'Dec' THEN '12' "
    "END)"
)


def _to_sortable_date(mon_yy: str) -> str:
    """Convert 'Mon YY' to '20YY-MM' for chronological comparison."""
    parts = mon_yy.split(' ')
    return f"20{parts[1]}-{_MONTH_NUM[parts[0]]}"


def _build_where(filters: dict) -> tuple[str, list]:
    """Build a dynamic WHERE clause from filter params.

    Returns (where_clause, params) where where_clause includes 'WHERE' if non-empty.
    """
    clauses = []
    params = []

    if filters.get("operators"):
        placeholders = ",".join("?" for _ in filters["operators"])
        clauses.append(f"i.operator IN ({placeholders})")
        params.extend(filters["operators"])

    if filters.get("date_start"):
        clauses.append(f"{_DATE_SORT_EXPR} >= ?")
        params.append(_to_sortable_date(filters["date_start"]))

    if filters.get("date_end"):
        clauses.append(f"{_DATE_SORT_EXPR} <= ?")
        params.append(_to_sortable_date(filters["date_end"]))

    if filters.get("properties"):
        placeholders = ",".join("?" for _ in filters["properties"])
        clauses.append(f"p.description IN ({placeholders})")
        params.extend(filters["properties"])

    if filters.get("categories"):
        placeholders = ",".join("?" for _ in filters["categories"])
        clauses.append(f"sd.product_category IN ({placeholders})")
        params.extend(filters["categories"])

    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return where, params


# All known expense type_descriptions
EXPENSE_TYPES = [
    "COMPRESSION",
    "CONSERVATION TAX",
    "ENVIRONMENTAL TAX (GAS)",
    "GATH-TRANS-OTHER DEDUCTS (OBO)",
    "GATHERING",
    "GATHERING FEE DEVON",
    "MARKETING FEE",
    "OTHER",
    "PROCESSING",
    "PRODUCTION TAX",
    "REGULATORY FEE",
    "SEVERANCE",
    "SEVERANCE TAX",
    "TRANSPORTATION",
]

# Grouped expense categories for cleaner display
EXPENSE_GROUPS = {
    "Gathering": ["GATHERING", "GATHERING FEE DEVON", "GATH-TRANS-OTHER DEDUCTS (OBO)"],
    "Processing": ["PROCESSING"],
    "Compression": ["COMPRESSION"],
    "Transportation": ["TRANSPORTATION"],
    "Marketing": ["MARKETING FEE"],
    "Taxes": ["CONSERVATION TAX", "ENVIRONMENTAL TAX (GAS)", "PRODUCTION TAX",
              "REGULATORY FEE", "SEVERANCE", "SEVERANCE TAX"],
    "Other": ["OTHER"],
}


def get_filter_options(conn: sqlite3.Connection) -> dict:
    """Get distinct values for all filter dropdowns."""
    operators = [r[0] for r in conn.execute(
        "SELECT DISTINCT operator FROM invoices ORDER BY operator"
    )]
    properties = [r[0] for r in conn.execute(
        "SELECT DISTINCT description FROM properties ORDER BY description"
    )]
    categories = [r[0] for r in conn.execute(
        "SELECT DISTINCT product_category FROM statement_details ORDER BY product_category"
    )]
    dates = conn.execute(
        "SELECT MIN(production_date), MAX(production_date) FROM statement_details"
    ).fetchone()

    # Get all distinct production dates for the date dropdowns (sorted)
    all_dates = [r[0] for r in conn.execute(
        "SELECT DISTINCT production_date FROM statement_details ORDER BY production_date"
    )]

    return {
        "operators": operators,
        "properties": properties,
        "categories": categories,
        "date_min": dates[0],
        "date_max": dates[1],
        "all_dates": all_dates,
    }


def get_monthly_rollup(conn: sqlite3.Connection, filters: dict = None) -> list[dict]:
    """Get monthly aggregated data with $/MCF calculations.

    Groups by production_date and computes revenue, volume, expense breakdowns.
    """
    filters = filters or {}
    where, params = _build_where(filters)

    # Build expense group CASE expressions
    expense_cols = []
    for group_name, types in EXPENSE_GROUPS.items():
        placeholders = ",".join(f"'{t}'" for t in types)
        col_name = group_name.lower().replace(" ", "_")
        expense_cols.append(
            f"SUM(CASE WHEN sd.type_description IN ({placeholders}) "
            f"THEN ABS(sd.owner_value) ELSE 0 END) as {col_name}_expense"
        )

    expense_sql = ",\n        ".join(expense_cols)

    sql = f"""
        SELECT
            sd.production_date,
            SUM(CASE WHEN sd.type_description IN ('ROYALTY INTEREST', 'RI')
                THEN sd.owner_value ELSE 0 END) as revenue,
            SUM(CASE WHEN sd.type_description IN ('ROYALTY INTEREST', 'RI')
                THEN sd.owner_volume ELSE 0 END) as volume,
            AVG(CASE WHEN sd.type_description IN ('ROYALTY INTEREST', 'RI')
                THEN sd.property_price END) as avg_price,
            SUM(CASE WHEN sd.type_description NOT IN ('ROYALTY INTEREST', 'RI')
                THEN ABS(sd.owner_value) ELSE 0 END) as total_expenses,
            {expense_sql}
        FROM statement_details sd
        JOIN properties p ON sd.statement_id = p.statement_id
        JOIN invoices i ON p.invoice_id = i.invoice_id
        {where}
        GROUP BY sd.production_date
        ORDER BY sd.production_date
    """

    rows = conn.execute(sql, params).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        vol = d["volume"] or 0
        # Calculate $/MCF ratios
        d["revenue_per_mcf"] = d["revenue"] / vol if vol else None
        d["total_expenses_per_mcf"] = d["total_expenses"] / vol if vol else None
        d["net_per_mcf"] = (d["revenue"] - d["total_expenses"]) / vol if vol else None

        for group_name in EXPENSE_GROUPS:
            col = group_name.lower().replace(" ", "_") + "_expense"
            per_mcf_col = group_name.lower().replace(" ", "_") + "_per_mcf"
            d[per_mcf_col] = d[col] / vol if vol else None

        result.append(d)

    return result


def get_raw_details(conn: sqlite3.Connection, filters: dict = None) -> list[dict]:
    """Get all statement detail rows with JOINed property/invoice info."""
    filters = filters or {}
    where, params = _build_where(filters)

    sql = f"""
        SELECT
            sd.production_date,
            i.operator,
            p.description as property,
            sd.product_category as category,
            sd.code,
            sd.type_description,
            sd.property_volume as volume,
            sd.property_price as price,
            sd.property_value as value,
            sd.owner_pct,
            sd.owner_volume,
            sd.owner_value,
            sd.btu
        FROM statement_details sd
        JOIN properties p ON sd.statement_id = p.statement_id
        JOIN invoices i ON p.invoice_id = i.invoice_id
        {where}
        ORDER BY sd.production_date, i.operator, p.description
    """

    return [dict(row) for row in conn.execute(sql, params)]


def get_invoice_list(conn: sqlite3.Connection) -> list[dict]:
    """Get all invoices for the invoice selector dropdown."""
    sql = """
        SELECT
            invoice_id, doc_type, operator, owner_number, check_number,
            invoice_date, op_acct_month, received_date, status,
            total_revenue, total_tax, total_deductions, total_amount
        FROM invoices
        ORDER BY invoice_date DESC, operator
    """
    return [dict(row) for row in conn.execute(sql)]


def get_invoice_detail(conn: sqlite3.Connection, invoice_id: int) -> dict | None:
    """Get full invoice detail with properties and statement details."""
    # Invoice header
    invoice = conn.execute(
        "SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,)
    ).fetchone()
    if not invoice:
        return None

    invoice_dict = dict(invoice)

    # Properties for this invoice
    properties = conn.execute(
        """SELECT * FROM properties WHERE invoice_id = ?
           ORDER BY description""",
        (invoice_id,)
    ).fetchall()

    props = []
    for prop in properties:
        p = dict(prop)
        # Statement details for this property
        details = conn.execute(
            """SELECT * FROM statement_details WHERE statement_id = ?
               ORDER BY product_category, type_description""",
            (prop["statement_id"],)
        ).fetchall()
        p["details"] = [dict(d) for d in details]
        props.append(p)

    invoice_dict["properties"] = props
    return invoice_dict
