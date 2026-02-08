"""Configuration for EnergyLink scraper."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project directory
PROJECT_DIR = Path(__file__).parent
load_dotenv(PROJECT_DIR / ".env")

# EnergyLink site
ENERGYLINK_URL = "https://app.energylink.com"
LOGIN_URL = f"{ENERGYLINK_URL}/"
DASHBOARD_URL = f"{ENERGYLINK_URL}/Core/BSP/Dashboard"
INVOICES_URL = f"{ENERGYLINK_URL}/Core/BSP/Dashboard#invoices"

# Credentials from .env
USERNAME = os.getenv("ENERGYLINK_USERNAME", "")
PASSWORD = os.getenv("ENERGYLINK_PASSWORD", "")

# Database
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "energylink.db"

# Browser state (persistent context for cookies/MFA trust)
BROWSER_STATE_PATH = DATA_DIR / "browser_state"

# Flags - override via command-line args
DEBUG = False       # True = process only first unprocessed invoice

# MFA timeout (milliseconds) - how long to wait for user to enter MFA code
MFA_TIMEOUT = 300_000  # 5 minutes

# Timeouts (milliseconds)
NAV_TIMEOUT = 30_000        # page navigation timeout
LOAD_TIMEOUT = 15_000       # element load/wait timeout
GRID_TIMEOUT = 20_000       # AG Grid render timeout

# Rate limiting (seconds)
PAGE_DELAY = 1.5            # delay between page loads
