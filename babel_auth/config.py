from datetime import timedelta
import os
from dotenv import load_dotenv
from auxillary_packages.errors import Missing_Configuration_Error

CWD = os.path.dirname(__file__)
load_dotenv(os.path.join(CWD, ".env"), override=True)

class FlaskConfig:
    try:
        # Security Metadata
        SECRET_KEY = os.environ["SECRET_KEY"]
        SIGNING_KEY = os.environ["SIGNING_KEY"]
        SESSION_COOKIE_SECURE = bool(os.environ["SESSION_COOKIE_SECURE"])

        # Database Metadata
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(CWD, os.environ["AUTH_DB_URI"])
        SQLALCHEMY_TRACK_MODIFICATIONS = bool(os.environ.get("TRACK_MODIFICATIONS", False))

        # Session Metadata
        PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.environ["SESSION_LIFETIME"]))

        # Deployment Metadata
        PORT = int(os.environ["PORT"])
        HOST = os.environ["HOST"]
        RESOURCE_SERVER_ORIGIN = os.environ["RS_DOMAIN"].lower()
        PROTOCOL = os.environ.get("RS_COMMUNICATION_PROTOCOL", "http").lower()
    except KeyError as e:
        raise Missing_Configuration_Error(f"FAILED TO SETUP CONFIGURATIONS FOR FLASK AUTH APPLICATION AS ENVIRONMENT VARIABLES WERE NOT FOUND (SEE: class Flask_Config at '{__file__}')")
    except TypeError as e:
        raise TypeError(f"FAILURE IN CONFIGURING ENVIRONMENT VARIABLE(S) OF TYPE: INT (SEE: class Flask_Config at '{__file__}')")
    
flaskconfig = FlaskConfig()