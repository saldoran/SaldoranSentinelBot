#!/usr/bin/env python3
"""
Entry point для SaldoranSentinelBot
"""

import sys
import os
from pathlib import Path

# Добавляем src в Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Импортируем и запускаем main из src
from main import run_service

if __name__ == "__main__":
    run_service()