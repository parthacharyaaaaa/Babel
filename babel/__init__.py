from flask import Flask
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import redis

from babel.config import flask_config

app = Flask(__name__)
app.config.from_object(flask_config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)

REDIS_INTERFACE = redis.Redis(host="localhost", port=1234, db = 0, health_check_interval = 60)

from babel import routes
from babel import models