from flask import url_for, redirect, render_template, jsonify, request

from babel import app, db, bcrypt, login_manager
from babel.models import *
from babel.config import *
from babel.errors import *
from googletrans import Translator

#Login Configurations
@login_manager.user_loader
def load_user(user_id : int):
    return User.query.filter_by(id = user_id).first()
login_manager.login_view = "login"

#View Functions

#Homepage
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

#History Management
@app.route("/history", methods = ["GET"])
def history():
    return render_template("history.html")

@app.route("/fetch-history", methods = ["GET"])
def fetch_history():
    pass

#Transcriptions and Translations
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
    try:
        #Ensure response integrity
        if not request.is_json:
            raise Unexpected_Request_Format("Response is not JSON serialized")
        
        translation_request = request.get_json(force=True, silent=False)

        original_text : str = translation_request["text"]
        dest_language : str = translation_request["dest"]
        src_language : str = translation_request.get("src", None)

        if original_text.strip() == "" or dest_language.strip() == "":
            raise ValueError("Invalid Request")
        
        translator = Translator()

        translation_metadata = translator.translate(text = original_text, dest = dest_language, src = src_language or 'auto')
        translated_text, translation_src = translation_metadata.text, translation_metadata.src
        print(translation_src)

        return jsonify({"translated-text" : translated_text, "src" : translation_src}), 200

    except Unexpected_Request_Format as e:
        print("NOT JSON")
        return jsonify({"error" : "yeah yeah"}), 400
    except KeyError as e:
        print("JSON NOT PROPER KWARGS")
        return jsonify("Invalid Request"), 400

@app.route("/fetch-languages", methods = ["GET"])
def fetch_languages():
    available_languages = {"auto" : "auto-detect"}
    available_languages.update(AVAILABLE_LANGUAGES)
    return jsonify({"lang" : available_languages}), 200