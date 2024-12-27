from babel import app, db, RedisManager
from babel.models import User
from flask import render_template, request, make_response
from sqlalchemy import select
from werkzeug.exceptions import NotFound
from auxillary_packages.decorators import CSRF_protect
import jwt
import os
from datetime import timedelta
import orjson

@app.route("/", methods = ["GET", "POST"])
@CSRF_protect
def home():
    return render_template("home.html")

@app.route("/signup", methods = ["GET"])
@app.route("/login", methods = ["GET"])
@CSRF_protect
def auth():
    r = make_response(render_template("auth.html", form_type=request.path[1:]))
    return r

@app.route("/history", methods = ["GET"])
@CSRF_protect
def history():
   return render_template("history.html")

@app.route("/transcript", methods = ["GET"])
@CSRF_protect
def transcript():
    return render_template("transcript.html")

@app.route("/translate", methods = ["GET"])
@CSRF_protect
def translate():
    return render_template("translate.html")

@app.route("/dashboard", methods = ["GET"])
@CSRF_protect
def dashboard():
    username = request.args.get("user")
    cached_result = RedisManager.get(f"usr:{username}")
    if cached_result:
        user = orjson.loads(cached_result)
        return render_template("dashboard.html",
                            username = username,
                            time_created = user["time_created"],
                            last_login = user["last_login"],
                            transcriptions = user["transcriptions"],
                            translations = user["translations"],
                            email_id = user["email_id"],
                            owner = user["isOwner"])
    if not username:
        raise NotFound("User not found! Make sure you've spelt their name right, and that this account actually exists")

    user = db.session.execute(select(User).where(User.username == username, User.deleted == False)).scalar_one_or_none()
        
    if not user:
        raise NotFound("This username is not registered with Babel. Make sure you spell it correctly, and that your queried username is actually registered. If you believe that this is your account, please contact support")
    
    tkn = request.cookies.get("access", request.cookies.get("Access"))
    isOwner : bool = False
    if tkn:
        dTkn : str = jwt.decode(tkn,
                                key = os.environ["SIGNING_KEY"],
                                algorithms=["HS256"],
                                leeway=timedelta(minutes=3))
        isOwner = dTkn["sub"] == user.username

    RedisManager.setex(f"usr:{username}", 180, orjson.dumps({"time_created" : user.time_created,
                            "last_login" : user.last_login,
                            "transcriptions" : user.transcriptions,
                            "translations" : user.translations,
                            "email_id" : user.email_id,
                            "isOwner" : isOwner}))

    return render_template("dashboard.html",
                            username = username,
                            time_created = user.time_created,
                            last_login = user.last_login,
                            transcriptions = user.transcriptions,
                            translations = user.translations,
                            email_id = user.email_id,
                            owner = isOwner)
