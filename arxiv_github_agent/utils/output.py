"""Utilities for saving outputs."""
import os
import json
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def save_json(obj: Any, filename: str) -> str:
    ensure_data_dir()
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path
