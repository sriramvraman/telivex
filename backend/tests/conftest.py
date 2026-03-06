"""Pytest configuration — ensure backend root is on sys.path."""

import sys
from pathlib import Path

# Add backend directory to path so `app.*` imports work
sys.path.insert(0, str(Path(__file__).parent.parent))
