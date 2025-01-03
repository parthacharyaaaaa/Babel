from flask import Flask
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from auxillary_packages.RedisManager import REDIS_MANAGER
import os
from babel.config import flask_config

app = Flask(__name__)
app.config.from_object(flask_config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)

RedisManager = REDIS_MANAGER(os.environ["REDIS_HOST"],
                            os.environ["REDIS_PORT"],
                            os.environ["REDIS_DB"])

from babel import routes, views
from babel import models