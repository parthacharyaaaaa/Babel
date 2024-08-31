from babel import app, db, bcrypt, login_manager
from models import *
from config import *

@login_manager.user_loader
def load_user(user_id : int):
    return User.query.filter_by(id = user_id).first()
login_manager.login_view = "login"

@app.route("/", methods = ["GET", "POST"])
def home():
    pass

#Account Management (Signup, Login, Logout, Deletion)
@app.route("/signup", methods = ["GET", "POST"])
def signup():
    pass

@app.route("/login", methods = ["POST", "GET"])
def login():
    pass

@app.route("/logout", methods = ["POST"])
def logout():
    pass

@app.route("/delete-account", methods = ["DELETE"])
def delete_account():
    pass

#Homepage
@app.route("/", methods = ["GET", "POST"])
def home():
    pass

@app.route("/history", methods = ["GET"])
def history():
    pass

@app.route("/fetch-history", methods = ["GET"])
def fetch_history():
    pass

@app.route("/transcript-text", methods = ["POST"])
def transcript_text():
    pass

@app.route("/translate", methods = ["POST"])
def translate():
    pass