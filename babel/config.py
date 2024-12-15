from datetime import timedelta
import os
import json
import functools
from dotenv import load_dotenv
from babel.auxillary.errors import Missing_Configuration_Error
from typing import Literal
from redis import Redis
import redis.exceptions as RedisExceptions
from redis.typing import ResponseT

CWD = os.path.dirname(__file__)
load_dotenv(os.path.join(CWD, ".env"), override=True)

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

class Cache_Manager:
    def __init__(self, host : str, port : int, db : int, startup_mandate : bool = False, error_behavior : Literal["lax", "strict"] = "strict", **kwargs):
        try:
            self.interface = Redis(host, port, db, kwargs)

            if startup_mandate and not self.interface.ping():
                raise ConnectionError("Redis Connection could not be established")
            elif not (startup_mandate and self.interface.ping()):
                print("\n\n===================WARNING: CACHE_MANAGER INSTANTIATED WITHOUT ACTIVE REDIS SERVER===================\n\n")

        except RedisExceptions.RedisError as e:
            raise ConnectionError("Failed to access cache banks")
        
        self.err_behavior = error_behavior
    def safe(func):
        @functools.wraps(func)
        def decorated(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except RedisExceptions.ConnectionError as e:
                # Logs for connection-related errors
                print(f"[Redis Error - ConnectionError] Failed to connect to Redis server. Details: {str(e)}")
            except RedisExceptions.TimeoutError as e:
                # Logs for timeout errors
                print(f"[Redis Error - TimeoutError] Redis operation timed out. Details: {str(e)}")
            except RedisExceptions.RedisError as e:
                # Logs for general Redis errors
                print(f"[Redis Error - RedisError] An unexpected Redis error occurred. Details: {str(e)}")
            except Exception as e:
                # Fallback for unexpected issues
                print(f"[Redis Error - Unknown] An unknown error occurred. Details: {str(e)}")

            if args[0].err_behavior == "strict":
                e = RedisExceptions.RedisError()
                e.__setattr__("description", "Raising error, error_policy = strict")
                raise e

            return None 
        return decorated

    @safe
    def setex(self, name : str | int, exp : int, value : str | int) -> None:
        self.interface.execute_command("SETEX", name, exp, value)

    @safe
    def delete(self, *names) -> None:
        self.interface.execute_command("DELETE", names)

    @safe
    def get(self, name) -> ResponseT | None:
        result = self.interface.execute_command("GET", name)
        if result != None:
            return result.decode("utf-8") if isinstance(result, bytes) else result
        return None
    
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