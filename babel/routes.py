from flask import url_for, redirect, render_template, jsonify, request
import time
from babel import app, db, bcrypt, login_manager
from babel.models import *
from babel.config import *
from babel.errors import *
from babel.transciber import getAudioTranscription
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
        if not request.is_json:         #JSON Serialize check
            raise Unexpected_Request_Format("Response is not JSON serialized")
        
        translation_request = request.get_json(force=True, silent=False)            #Parsing JSON response, silent is kept at False just as a second measure in case .is_json fails

        original_text : str = translation_request["text"]
        dest_language : str = translation_request["dest"].lower()
        src_language : str = translation_request.get("src", None)
        src_language = None if src_language.strip() == "" else src_language.lower()

        #Validating strings
        if original_text.strip() == "" or dest_language.strip() == "":
            raise ValueError("Invalid Request")

        #Validating requested languages
        if dest_language not in AVAILABLE_LANGUAGES:
            return jsonify({"error" : "Destination Language Not Found"}), 404
        if src_language is not None and src_language not in AVAILABLE_LANGUAGES:
            return jsonify({"error" : "Source Language Not Found"}), 404

        #Initialize Translation Process
        start_time = time.time()
        translator = Translator()

        translation_metadata = translator.translate(text = original_text, dest = dest_language, src = src_language or 'auto')

        translated_text, translation_src = translation_metadata.text, translation_metadata.src
        time_taken = time.time() - start_time

        return jsonify({"translated-text" : translated_text, "src" : translation_src, "time" : time_taken}), 200

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