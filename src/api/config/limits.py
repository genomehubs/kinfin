# src/config/limits.py
import os

LIMIT_INIT = os.getenv("KINFIN_LIMIT_INIT", "1/minute")
LIMIT_STANDARD = os.getenv("KINFIN_LIMIT_STANDARD", "60/minute")
LIMIT_LOW = os.getenv("KINFIN_LIMIT_LOW", "300/minute")
