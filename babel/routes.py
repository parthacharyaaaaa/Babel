from flask import url_for, redirect, render_template, jsonify, request

from babel import app, db, bcrypt, login_manager
from babel.models import *
from babel.config import *

@login_manager.user_loader
def load_user(user_id : int):
    return User.query.filter_by(id = user_id).first()
login_manager.login_view = "login"

@app.route("/", methods = ["GET", "POST"])
def home():
    return render_template("home.html")

#Account Management (Signup, Login, Logout, Deletion)
@app.route("/signup", methods = ["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

@app.route("/login", methods = ["POST", "GET"])
def login():
    if request.method == "POST":
        return render_template("login.html")

@app.route("/logout", methods = ["POST"])
def logout():
    pass

@app.route("/delete-account", methods = ["DELETE"])
def delete_account():
    pass

@app.route("/history", methods = ["GET"])
def history():
    return render_template("history.html")

@app.route("/fetch-history", methods = ["GET"])
def fetch_history():
    pass

@app.route("/trancript", methods = ["GET"])
def transcript():
    return render_template("transcript.html")

@app.route("/translate", methods = ["GET"])
def translate():
    return render_template("translate.html")

@app.route("/transcript-text", methods = ["POST"])
def transcript_text():
    pass

@app.route("/translate-text", methods = ["POST"])
def translate_text():
    pass