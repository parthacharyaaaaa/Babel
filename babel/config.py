from datetime import timedelta
import os
import json
from dotenv import load_dotenv
from babel.auxillary.errors import Missing_Configuration_Error

CWD = os.path.dirname(__file__)
load_dotenv()

class Flask_Config:
    """Flask app configuration."""
    try:
        SECRET_KEY = os.environ["SECRET_KEY"]
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(CWD, os.environ["RS_DATABASE_URI"])
        TRACK_MODIFICATIONS = bool(os.environ.get("TRACK_MODIFICATIONS", False))
        PORT = os.environ["PORT"]
        HOST = os.environ["HOST"]
        PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.environ["SESSION_LIFETIME"]))
        UPLOAD_FOLDER = os.path.join(CWD, os.environ["UPLOAD_FOLDER"])
        MAX_CONTENT_LENGTH = int(os.environ["MAX_CONTENT_LENGTH"])
    except KeyError as e:
        raise Missing_Configuration_Error(f"FAILED TO SETUP CONFIGURATIONS FOR FLASK APPLICATION AS ENVIRONMENT VARIABLES WERE NOT FOUND (SEE: class Flask_Config at '{__file__}')")
    except TypeError as e:
        raise TypeError(f"FAILURE IN CONFIGURING ENVIRONMENT VARIABLE(S) OF TYPE: INT (SEE: class Flask_Config at '{__file__}')")

class AssemblyAI_Config:
    """AssemblyAI configuration."""
    UPLOAD_URL = 'https://api.assemblyai.com/v2/upload'
    TRANSCRIPT_URL = 'https://api.assemblyai.com/v2/transcript'
    AAI_API_KEY = os.environ.get("ASSEMBLY_AI_API_KEY", None)

    if AAI_API_KEY is None:
        raise Missing_Configuration_Error(f"ASSEMBLY-AI API KEY NOT FOUND! SEE CLASS AssemblyAI_Config IN {__file__}")
    
    if not AAI_API_KEY.isalnum():
        raise ValueError(f"ASSEMBLY-AI API KEY IS INVALID. MUST BE STRINCTLY ALPHA-NUMERIC, NOT {AAI_API_KEY}")

#Translation
print(os.path.join(CWD, os.environ["AVAILABLE_LANGUAGES"]))
try:
    with open(os.path.join(CWD, os.environ["AVAILABLE_LANGUAGES"]), "r") as languages_filepath:
        AVAILABLE_LANGUAGES = json.load(languages_filepath)
        if not isinstance(AVAILABLE_LANGUAGES, dict):
            raise ValueError("INVALID FORMAT DETECTED IN file: lang.json (NOT KEY-VALUE PAIRS)")
except KeyError:
    raise Missing_Configuration_Error("FAILURE IN LOADING JSON CONFIGURATIONS FILEPATH FROM ENVIRONMENT VARIABLES (lang.json)")
except FileNotFoundError:
    raise Missing_Configuration_Error("FAILURE IN LOCATING JSON CONFIGURATIONS FILE (lang.json)")


flask_config = Flask_Config()
aai_config = AssemblyAI_Config()