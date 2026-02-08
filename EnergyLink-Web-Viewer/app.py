"""EnergyLink Web Viewer - Flask application."""

import argparse
import socket
import sqlite3
import threading
import webbrowser
from pathlib import Path

from flask import Flask, g, render_template

# DB can live at ../data/energylink.db (dev) or ./data/energylink.db (distributed)
_APP_DIR = Path(__file__).parent
DB_PATH = _APP_DIR / "data" / "energylink.db"
if not DB_PATH.exists():
    DB_PATH = _APP_DIR.parent / "data" / "energylink.db"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(str(DB_PATH))
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def create_app(debug=False):
    app = Flask(__name__)
    app.config["DEBUG"] = debug

    app.teardown_appcontext(close_db)

    from blueprints.dashboard import bp as dashboard_bp
    from blueprints.invoices import bp as invoices_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(invoices_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    return app


def find_open_port(start=50000, end=50049):
    """Scan ports start..end and return the first available one."""
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No open port found in range {start}-{end}")


def open_browser(url, delay=1.0):
    """Open the browser after a short delay to let Flask start."""
    def _open():
        import time
        time.sleep(delay)
        webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EnergyLink Web Viewer")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    parser.add_argument("--port", type=int, default=0, help="Port number (0 = auto)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    args = parser.parse_args()

    port = args.port if args.port else find_open_port()

    app = create_app(debug=args.debug)

    if not args.no_browser and not args.debug:
        open_browser(f"http://127.0.0.1:{port}")

    print(f"Starting EnergyLink Viewer on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=args.debug)
