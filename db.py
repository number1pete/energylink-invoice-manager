"""SQLite database schema and helper functions for EnergyLink scraper."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS scrape_runs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at      TEXT NOT NULL,
            finished_at     TEXT,
            status          TEXT NOT NULL DEFAULT 'running',
            invoices_processed INTEGER DEFAULT 0,
            invoices_skipped   INTEGER DEFAULT 0,
            error_message   TEXT
        );

        CREATE TABLE IF NOT EXISTS scrape_logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id    INTEGER NOT NULL REFERENCES scrape_runs(id),
            timestamp TEXT NOT NULL,
            level     TEXT NOT NULL,
            message   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id     INTEGER UNIQUE NOT NULL,
            doc_type       TEXT,
            operator       TEXT,
            owner_number   TEXT,
            check_number   TEXT,
            invoice_date   TEXT,
            op_acct_month  TEXT,
            received_date  TEXT,
            status         TEXT,
            total_revenue  REAL,
            total_tax      REAL,
            total_deductions REAL,
            total_amount   REAL,
            scraped_at     TEXT NOT NULL,
            run_id         INTEGER REFERENCES scrape_runs(id)
        );

        CREATE TABLE IF NOT EXISTS properties (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id           INTEGER NOT NULL REFERENCES invoices(invoice_id),
            statement_id         INTEGER UNIQUE NOT NULL,
            cost_center          TEXT,
            description          TEXT,
            state                TEXT,
            county               TEXT,
            owner_share_revenue  REAL,
            tax                  REAL,
            deductions           REAL,
            total                REAL,
            scraped_at           TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS statement_details (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            statement_id      INTEGER NOT NULL REFERENCES properties(statement_id),
            product_category  TEXT,
            code              TEXT,
            type_description  TEXT,
            production_date   TEXT,
            btu               REAL,
            property_volume   REAL,
            property_price    REAL,
            property_value    REAL,
            owner_pct         REAL,
            distribution_pct  REAL,
            owner_volume      REAL,
            owner_value       REAL
        );
    """)
    conn.commit()


# --- Scrape run helpers ---

def create_run(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        "INSERT INTO scrape_runs (started_at, status) VALUES (?, 'running')",
        (_now(),),
    )
    conn.commit()
    return cur.lastrowid


def finish_run(conn: sqlite3.Connection, run_id: int, status: str,
               invoices_processed: int = 0, invoices_skipped: int = 0,
               error_message: str = None) -> None:
    conn.execute(
        """UPDATE scrape_runs
           SET finished_at = ?, status = ?, invoices_processed = ?,
               invoices_skipped = ?, error_message = ?
           WHERE id = ?""",
        (_now(), status, invoices_processed, invoices_skipped, error_message, run_id),
    )
    conn.commit()


def log(conn: sqlite3.Connection, run_id: int, level: str, message: str) -> None:
    conn.execute(
        "INSERT INTO scrape_logs (run_id, timestamp, level, message) VALUES (?, ?, ?, ?)",
        (run_id, _now(), level, message),
    )
    conn.commit()


# --- Invoice helpers ---

def invoice_exists(conn: sqlite3.Connection, invoice_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM invoices WHERE invoice_id = ?", (invoice_id,)
    ).fetchone()
    return row is not None


def insert_invoice(conn: sqlite3.Connection, run_id: int, data: dict) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO invoices
           (invoice_id, doc_type, operator, owner_number, check_number,
            invoice_date, op_acct_month, received_date, status,
            total_revenue, total_tax, total_deductions, total_amount,
            scraped_at, run_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["invoice_id"],
            data.get("doc_type"),
            data.get("operator"),
            data.get("owner_number"),
            data.get("check_number"),
            data.get("invoice_date"),
            data.get("op_acct_month"),
            data.get("received_date"),
            data.get("status"),
            data.get("total_revenue"),
            data.get("total_tax"),
            data.get("total_deductions"),
            data.get("total_amount"),
            _now(),
            run_id,
        ),
    )
    conn.commit()


# --- Property helpers ---

def insert_property(conn: sqlite3.Connection, invoice_id: int, data: dict) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO properties
           (invoice_id, statement_id, cost_center, description, state, county,
            owner_share_revenue, tax, deductions, total, scraped_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            invoice_id,
            data["statement_id"],
            data.get("cost_center"),
            data.get("description"),
            data.get("state"),
            data.get("county"),
            data.get("owner_share_revenue"),
            data.get("tax"),
            data.get("deductions"),
            data.get("total"),
            _now(),
        ),
    )
    conn.commit()


# --- Statement detail helpers ---

def insert_statement_detail(conn: sqlite3.Connection, statement_id: int, data: dict) -> None:
    conn.execute(
        """INSERT INTO statement_details
           (statement_id, product_category, code, type_description,
            production_date, btu, property_volume, property_price,
            property_value, owner_pct, distribution_pct,
            owner_volume, owner_value)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            statement_id,
            data.get("product_category"),
            data.get("code"),
            data.get("type_description"),
            data.get("production_date"),
            data.get("btu"),
            data.get("property_volume"),
            data.get("property_price"),
            data.get("property_value"),
            data.get("owner_pct"),
            data.get("distribution_pct"),
            data.get("owner_volume"),
            data.get("owner_value"),
        ),
    )
    conn.commit()
