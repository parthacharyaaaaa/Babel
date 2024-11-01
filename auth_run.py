from babel_auth import auth, db
from babel_auth.models import Token

if __name__ == "__main__":
    with auth.app_context():
        db.create_all()
    
    auth.run(host=auth.config["HOST"], port = auth.config["PORT"])