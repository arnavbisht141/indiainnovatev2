import sys
import os

# Add the 'backend' folder to the python path so the fastApi app can import its modules
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
sys.path.append(backend_path)

from app.main import app
