"""Dashboard API endpoints."""

from flask import Blueprint, jsonify, request

from app import get_db
import db_queries

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


def _parse_filters() -> dict:
    """Parse filter query params from the request."""
    filters = {}

    operators = request.args.getlist("operators")
    if operators:
        filters["operators"] = operators

    date_start = request.args.get("date_start")
    if date_start:
        filters["date_start"] = date_start

    date_end = request.args.get("date_end")
    if date_end:
        filters["date_end"] = date_end

    properties = request.args.getlist("properties")
    if properties:
        filters["properties"] = properties

    categories = request.args.getlist("categories")
    if categories:
        filters["categories"] = categories

    return filters


@bp.route("/filters")
def filters():
    conn = get_db()
    return jsonify(db_queries.get_filter_options(conn))


@bp.route("/monthly")
def monthly():
    conn = get_db()
    filters = _parse_filters()
    return jsonify(db_queries.get_monthly_rollup(conn, filters))


@bp.route("/details")
def details():
    conn = get_db()
    filters = _parse_filters()
    return jsonify(db_queries.get_raw_details(conn, filters))
