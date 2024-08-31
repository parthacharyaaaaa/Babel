from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SESSION_LIFETIME = timedelta(days = int(os.environ.get("SESSION_LIFETIME")))
SECRET_KEY = os.environ.get("SESSION_KEY")
TRACK_MODIFICATIONS : bool = os.environ.get("TRACK_MODIFICATIONS")
