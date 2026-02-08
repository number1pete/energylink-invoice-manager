"""EnergyLink Scraper - Main orchestrator.

Scrapes oil & gas royalty invoices, properties, and statement details
from the EnergyLink portal and stores them in SQLite.

Always runs headed so the user can complete MFA if needed.

Usage:
    python scraper.py                  # normal mode
    python scraper.py --debug          # process only first unprocessed invoice
"""

import argparse
import sys
import traceback

import config
import db
from browser import (
    launch_browser,
    close_browser,
    login,
    navigate_to_invoices,
    navigate_to_invoice_summary,
    navigate_to_statement,
    MFARequiredError,
    LoginError,
)
from parsers import parse_invoice_list, parse_invoice_summary, parse_statement_details


def main():
    args = parse_args()
    config.DEBUG = args.debug

    # Initialize database
    conn = db.get_connection()
    db.init_db(conn)
    run_id = db.create_run(conn)
    db.log(conn, run_id, "INFO", f"Scrape run started (debug={config.DEBUG})")

    pw = None
    context = None
    invoices_processed = 0
    invoices_skipped = 0

    try:
        # Launch browser and login
        db.log(conn, run_id, "INFO", "Launching browser...")
        pw, context, page = launch_browser()

        db.log(conn, run_id, "INFO", "Attempting login...")
        login(page)
        db.log(conn, run_id, "INFO", "Login successful")

        # Navigate to invoices list
        db.log(conn, run_id, "INFO", "Navigating to invoices list...")
        navigate_to_invoices(page)

        # Parse invoice list from all pages
        db.log(conn, run_id, "INFO", "Parsing invoice list...")
        all_invoices = parse_invoice_list(page)
        db.log(conn, run_id, "INFO", f"Found {len(all_invoices)} invoices in grid")

        # Filter to unprocessed invoices
        unprocessed = []
        for inv in all_invoices:
            if db.invoice_exists(conn, inv["invoice_id"]):
                invoices_skipped += 1
            else:
                unprocessed.append(inv)

        db.log(conn, run_id, "INFO",
               f"{len(unprocessed)} new invoices to process, {invoices_skipped} already in DB")

        if config.DEBUG and unprocessed:
            unprocessed = [unprocessed[0]]
            db.log(conn, run_id, "INFO", "DEBUG mode: processing only first unprocessed invoice")

        # Process each invoice
        for inv in unprocessed:
            invoice_id = inv["invoice_id"]
            db.log(conn, run_id, "INFO", f"Processing invoice {invoice_id}...")

            try:
                # Navigate to invoice summary
                navigate_to_invoice_summary(page, invoice_id)

                # Parse invoice summary (financials + properties)
                summary = parse_invoice_summary(page, invoice_id)

                # Merge grid data with summary data
                invoice_data = {**inv}
                if summary.get("check_number"):
                    invoice_data["check_number"] = summary["check_number"]
                if summary.get("total_revenue") is not None:
                    invoice_data["total_revenue"] = summary["total_revenue"]
                if summary.get("total_tax") is not None:
                    invoice_data["total_tax"] = summary["total_tax"]
                if summary.get("total_deductions") is not None:
                    invoice_data["total_deductions"] = summary["total_deductions"]
                if summary.get("total_amount") is not None:
                    invoice_data["total_amount"] = summary["total_amount"]

                # Insert invoice record
                db.insert_invoice(conn, run_id, invoice_data)
                db.log(conn, run_id, "INFO",
                       f"Inserted invoice {invoice_id}: {invoice_data.get('operator')} "
                       f"check #{invoice_data.get('check_number')}")

                # Process each property/statement
                properties = summary.get("properties", [])
                db.log(conn, run_id, "INFO",
                       f"Invoice {invoice_id} has {len(properties)} properties")

                for prop in properties:
                    statement_id = prop["statement_id"]

                    try:
                        # Insert property record
                        db.insert_property(conn, invoice_id, prop)

                        # Navigate to statement detail
                        navigate_to_statement(page, statement_id)

                        # Parse statement details
                        details = parse_statement_details(page, statement_id)
                        db.log(conn, run_id, "INFO",
                               f"Statement {statement_id}: {len(details)} line items")

                        # Insert each line item
                        for detail in details:
                            db.insert_statement_detail(conn, statement_id, detail)

                    except Exception as e:
                        db.log(conn, run_id, "WARNING",
                               f"Error processing statement {statement_id}: {e}")
                        continue

                invoices_processed += 1

            except Exception as e:
                db.log(conn, run_id, "WARNING",
                       f"Error processing invoice {invoice_id}: {e}")
                continue

        # Success
        db.finish_run(conn, run_id, "success",
                      invoices_processed=invoices_processed,
                      invoices_skipped=invoices_skipped)
        db.log(conn, run_id, "INFO",
               f"Scrape completed: {invoices_processed} processed, {invoices_skipped} skipped")
        print(f"Done: {invoices_processed} invoices processed, {invoices_skipped} skipped")

    except MFARequiredError as e:
        db.log(conn, run_id, "ERROR", f"MFA required: {e}")
        db.finish_run(conn, run_id, "mfa_required", error_message=str(e))
        print(f"MFA required - please log in manually and trust this device. {e}")
        sys.exit(1)

    except LoginError as e:
        db.log(conn, run_id, "ERROR", f"Login failed: {e}")
        db.finish_run(conn, run_id, "failure", error_message=str(e))
        print(f"Login failed: {e}")
        sys.exit(1)

    except Exception as e:
        tb = traceback.format_exc()
        db.log(conn, run_id, "ERROR", f"Unexpected error: {e}\n{tb}")
        db.finish_run(conn, run_id, "failure",
                      invoices_processed=invoices_processed,
                      invoices_skipped=invoices_skipped,
                      error_message=f"{e}\n{tb}")
        print(f"Error: {e}")
        sys.exit(1)

    finally:
        if pw and context:
            close_browser(pw, context)
        conn.close()


def parse_args():
    parser = argparse.ArgumentParser(description="EnergyLink royalty portal scraper")
    parser.add_argument("--debug", action="store_true",
                        help="Process only the first unprocessed invoice")
    return parser.parse_args()


if __name__ == "__main__":
    main()
