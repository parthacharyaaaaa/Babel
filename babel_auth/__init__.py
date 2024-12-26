import os
import json
from flask import Flask

from babel_auth.config import flaskconfig, CWD
from babel_auth.schema import TokenManager

auth = Flask(__name__)
auth.config.from_object(flaskconfig)

# Set up token manager
with open(os.path.join(CWD, os.environ["ACCESS_SCHEMA_FP"]), "r") as accessSchema:
    accessDict : dict = json.load(accessSchema)
with open(os.path.join(CWD, os.environ["REFRESH_SCHEMA_FP"]), "r") as refreshSchema:
    refreshDict : dict = json.load(refreshSchema)
tokenManager = TokenManager(signingKey=auth.config["SIGNING_KEY"],
                            accessSchema=accessDict,
                            refreshSchema=refreshDict)

from babel_auth import routes