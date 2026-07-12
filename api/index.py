import sys
import os

# Add the project root to the Python path so imports like `from app import create_app` work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run import app

# Vercel expects the WSGI callable to be named `app`
