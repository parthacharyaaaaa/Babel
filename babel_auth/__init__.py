from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

auth = Flask(__name__)

db = SQLAlchemy(auth)
migrate = Migrate(auth, db)

from babel_auth import routes
from babel_auth.schema import *