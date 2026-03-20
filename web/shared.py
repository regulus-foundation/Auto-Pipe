"""Shared state — avoids circular imports between app.py and routes."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
