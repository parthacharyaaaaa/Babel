from datetime import timedelta
import os
from dotenv import load_dotenv
import json
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

class Flask_Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SESSION_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI")
    TRACK_MODIFICATIONS = os.environ.get("TRACK_MODIFICATIONS")
    PORT = os.environ.get("PORT")
    HOST = os.environ.get("HOST")
    SESSION_LIFETIME = timedelta(days=int(os.environ.get("SESSION_LIFETIME")))

class AssemblyAI_Config:
    """AssemblyAI configuration."""
    UPLOAD_URL = 'https://api.assemblyai.com/v2/upload'
    TRANSCRIPT_URL = 'https://api.assemblyai.com/v2/transcript'
    AAI_API_KEY = os.environ.get("ASSEMBLY_AI_API_KEY")

#Translation
with open(os.environ.get("AVAILABLE_LANGUAGES"), "r") as languages_filepath:
    AVAILABLE_LANGUAGES = json.load(languages_filepath)

flask_config = Flask_Config()
aai_config = AssemblyAI_Config()