# conftest.py — project root pytest configuration
import sys
import os

# Ensure the project root is on the Python path so `backend.*` imports resolve
sys.path.insert(0, os.path.dirname(__file__))
