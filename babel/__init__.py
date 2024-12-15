from flask import Flask
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from babel.auxillary.Logger import Logger
import os
from babel.config import flask_config, Cache_Manager

app = Flask(__name__)
app.config.from_object(flask_config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)

RedisManager = Cache_Manager(os.environ["REDIS_HOST"],
                            os.environ["REDIS_PORT"],
                            os.environ["REDIS_DB"])

ErrorLogger = Logger(app.config["ERROR_LOG_FILE"])

from babel import routes
from babel import models