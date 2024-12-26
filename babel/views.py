from babel import app, db
from babel.models import User
from flask import render_template, request
from sqlalchemy import select
from werkzeug.exceptions import NotFound
import jwt
import os
from datetime import timedelta

@app.route("/", methods = ["GET", "POST"])
def home():
    return render_template("home.html")

@app.route("/signup", methods = ["GET"])
@app.route("/login", methods = ["GET"])
def auth():
    return render_template("auth.html", form_type=request.path[1:])

@app.route("/history", methods = ["GET"])
def history():
   return render_template("history.html")

@app.route("/transcript", methods = ["GET"])
def transcript():
    return render_template("transcript.html")

@app.route("/translate", methods = ["GET"])
def translate():
    return render_template("translate.html")

@app.route("/dashboard", methods = ["GET"])
def dashboard():
    username = request.args.get("user")
    if not username:
        raise NotFound("User not found! Make sure you've spelt their name right, and that this account actually exists")

    user = db.session.execute(select(User).where(User.username == username)).scalar_one_or_none()
        
    if not user:
        raise NotFound("This username is not registered with Babel. Make sure you spell it correctly, and that your queried username is actually registered. If you believe that this is your account, please contact support")
    
    isOwner : bool = False
    tkn = request.cookies.get("access", request.cookies.get("Access"))
    if tkn:
        dTkn : str = jwt.decode(tkn,
                                key = os.environ["SIGNING_KEY"],
                                algorithms=["HS256"],
                                leeway=timedelta(minutes=3))
        isOwner = dTkn["sub"] == user.username

    return render_template("dashboard.html",
                            username = username,
                            time_created = user.time_created,
                            last_login = user.last_login,
                            transcriptions = user.transcriptions,
                            translations = user.translations,
                            email_id = user.email_id,
                            owner = isOwner)
