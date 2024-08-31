from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from babel.config import *

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["PERMANENT_SESSION_LIFETIME"] = SESSION_LIFETIME
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = TRACK_MODIFICATIONS

db = SQLAlchemy(app)
migrate = Migrate(app)
login_manager = LoginManager(app)
bcrypt = Bcrypt(app)

from babel import routes