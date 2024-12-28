from datetime import timedelta
import os
import json
from dotenv import load_dotenv
from auxillary_packages.errors import Missing_Configuration_Error

CWD = os.path.dirname(__file__)
load_dotenv(os.path.join(CWD, ".env"), override=True)

class Flask_Config:
    """Flask app configuration."""
    try:
        # Security metadata
        SECRET_KEY = os.environ["SECRET_KEY"]
        CSP_STRING = os.environ["CSP_STRING"] + f" connect-src 'self' {os.environ['AUTH_SERVER_ADDRESS']};"
        PRIVATE_COMM_KEYS : list = os.environ["PRIVATE_COMM_KEYS"].split(",")

        # IP metadata
        VALID_PROXIES : list = os.environ["VALID_PROXIES"].split(",")
        PRIVATE_IP_ADDRS : list = os.environ["PRIVATE_IP_ADDRS"].split(",")

        # DB metadata
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(CWD, os.environ["RS_DATABASE_URI"])
        TRACK_MODIFICATIONS = bool(os.environ.get("TRACK_MODIFICATIONS", False))

        # Addressing metadata
        PORT = os.environ["PORT"]
        HOST = os.environ["HOST"]

        # File I/O metadata
        UPLOAD_FOLDER = os.environ["UPLOAD_FOLDER"]
        MAX_CONTENT_LENGTH = int(os.environ["MAX_CONTENT_LENGTH"])

        # Logging metadata
        ERROR_LOG_FILE = os.path.join(CWD, os.environ["ERROR_LOG_FILE"])

        # Auth Server Communication Metadata
        AUTH_SERVER_ORIGIN = os.environ["AUTH_SERVER_ADDRESS"]
        AUTH_COMMUNICATION_PROTOCOL = os.environ.get("AUTH_SERVER_COMMUNICATION_PROTOCOL", "http")

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