from babel import app, db
from babel.config import flask_config

HOST = flask_config.HOST
PORT = flask_config.PORT

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host = HOST, port = PORT, debug = True)