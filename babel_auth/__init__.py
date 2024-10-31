from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from babel_auth.config import flaskconfig

auth = Flask(__name__)
auth.config.from_object(flaskconfig)
db = SQLAlchemy(auth)
migrate = Migrate(auth, db)

from babel_auth import routes
from babel_auth.schema import *