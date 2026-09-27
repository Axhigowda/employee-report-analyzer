#!/usr/bin/env python3
"""
Employee Report Analyzer - Web UI Application

Run with:
    python app.py
    # or
    python app.py --port 8501
"""
import argparse
import sys
from pathlib import Path

# Add workspace to sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from src.ui.server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Employee Report Analyzer - Progress Scorecard Web UI")
    parser.add_argument("--port", type=int, default=8501, help="Port to bind server (default: 8501)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    args = parser.parse_args()

    run_server(port=args.port, host=args.host)


if __name__ == "__main__":
    main()
