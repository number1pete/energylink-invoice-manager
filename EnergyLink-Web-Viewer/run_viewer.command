#!/bin/bash
# EnergyLink Viewer - macOS launcher
# Double-click this file to start the app.

cd "$(dirname "$0")"

VENV_DIR=".venv"

# First run: create venv and install dependencies
if [ ! -d "$VENV_DIR" ]; then
    echo "First run - setting up Python environment..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet -r requirements.txt
    echo "Setup complete!"
    echo ""
fi

echo "Starting EnergyLink Viewer..."
"$VENV_DIR/bin/python" app.py
