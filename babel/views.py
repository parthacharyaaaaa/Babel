from babel import app
from flask import render_template, request

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