from babel import app, db
from babel.config import PORT, HOST
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host = HOST, port = PORT, debug = True)