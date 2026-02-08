"""Invoice API endpoints."""

from flask import Blueprint, jsonify

from app import get_db
import db_queries

bp = Blueprint("invoices", __name__, url_prefix="/api/invoices")


@bp.route("/")
def invoice_list():
    conn = get_db()
    return jsonify(db_queries.get_invoice_list(conn))


@bp.route("/<int:invoice_id>")
def invoice_detail(invoice_id):
    conn = get_db()
    result = db_queries.get_invoice_detail(conn, invoice_id)
    if result is None:
        return jsonify({"error": "Invoice not found"}), 404
    return jsonify(result)
