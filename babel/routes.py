from flask import url_for, redirect, render_template, jsonify, request, abort, g
import time
from babel import app, db, bcrypt
from babel.models import *
from babel.config import *
from babel.auxillary.errors import *
from babel.transciber import getAudioTranscription
from googletrans import Translator
from sqlalchemy import select, insert, update, union_all, Result
from sqlalchemy.exc import IntegrityError, DataError, StatementError

#View Functions
#Homepage
@app.route("/", methods = ["GET", "POST"])
def home():
    return render_template("home.html")

#Account Management (Signup, Login, Logout, Deletion)
@app.route("/signup", methods = ["GET"])
@app.route("/login", methods = ["GET"])
def auth():
    return render_template("auth.html", form_type=request.path[1:])

@app.route("/register", methods = ["POST"])
def register():
    if not request.is_json:
        raise Unexpected_Request_Format(f"POST /{request.path[1:]} Only accepts JSON requests")
    
    registrationDetails = request.get_json(force=True)
    try:
        uname : str = registrationDetails["username"]
        email : str = registrationDetails["email"]
        password : str = registrationDetails["pass"]
        cpassword : str = registrationDetails["cpass"]

        if password != cpassword:
            raise ValueError
    except KeyError as k:
        raise Unexpected_Request_Format(f"POST /{request.path[1:]} Mandatory field missing")
    except ValueError as v:
        raise Unexpected_Request_Format(f"POST /{request.path[1:]} Passwords do not match")

    userExists = db.session.execute(select(User).where(User.username == uname)).first()
    emailExists = db.session.execute(select(User).where(User.email_id == email)).first()

    if emailExists:
        return jsonify({"message" : "This email address is already registered, please log in or use a different email address"}), 409

    if userExists:
        return jsonify({"message" : "This username is already registered, please log in or use a different username"}), 409
    
    try:
        db.session.execute(insert(User).values(username = uname,
                                            password = bcrypt.generate_password_hash(password),
                                            email_id = email,
                                            time_created = datetime.now(),
                                            last_login = datetime.now(),
                                            deleted = False,
                                            time_deleted = None,
                                            transcriptions = 0,
                                            translations = 0))
        db.session.commit()
    except (IntegrityError, DataError, StatementError) as e:
        db.session.rollback()
        abort(500)
    
    return jsonify({"message" : "Account Registered Successfully"}), 201

@app.route("/delete-account", methods = ["DELETE"])
def delete_account():
    if not request.is_json:
        raise Unexpected_Request_Format(f"POST /{request.path[1:]} Only accepts JSON requests")
    
    password : str = request.get_json(force=True)["password"]
    if not password:
        raise Unexpected_Request_Format(f"POST /{request.path[1:]} Password missing")
    try:
        db.session.execute(update(User)
                           .where(User.email_id == g.decodedToken["sub"])
                           .values(deleted = True, time_deleted = datetime.now()))
        db.session.commit()
    except (DataError, StatementError):
        db.session.rollback()
        abort(500)
    # Logic for sending an API request to auth server to instantly delete all assosciated refresh tokens

#History Management
@app.route("/history", methods = ["GET"])
def history():
   return render_template("history.html")
    
@app.route("/fetch-history", methods = ["GET"])
def fetch_history():
    if not request.is_json:
        raise Unexpected_Request_Format(f"POST /{request.path[1:]} Only accepts JSON requests")
    
    username : str = g.decodedToken.get("sub", None)

    viewPreference : str = request.args.get("preference", "all")
    try:
        currentPage : int = int(request.args.get("page", 1))
    except ValueError:
        raise Unexpected_Request_Format(f"POST /{request.path[1:]} Requires an integer to indicate value result")
    perPage : int = 10

    transcriptionQuery = (select(Transcription_Request.id,
                                Transcription_Request.time_requested.label("time_requested"),
                                Transcription_Request.transcipted_text.label("content")
                                ).where(Transcription_Request.requestor == username)
                                .order_by(Transcription_Request.time_requested.desc())
                                .limit(perPage)
                                .offset((currentPage-1) * perPage))
    
    translationQuery = (select(Translation_Request.id,
                              Translation_Request.time_requested.label("time_requested"),
                              Translation_Request.language_from.label("src"),
                              Translation_Request.language_to.label("dst"),
                              ).where(Translation_Request.requested_by == username)
                              .order_by(Translation_Request.time_requested.desc())
                              .limit(perPage)
                              .offset((currentPage-1) * perPage))
    
    combinedQuery = (transcriptionQuery.union_all(translationQuery)
                    .order_by(db.desc("time_requested"))
                    .limit(perPage)
                    .offset((currentPage - 1) * perPage))
    
    try:
        if viewPreference == "transcription":
            qResult = db.session.execute(transcriptionQuery)
        elif viewPreference == "translation":
            qResult = db.session.execute(translationQuery)
        else:
            qResult = db.session.execute(combinedQuery)
    except (IntegrityError, DataError):
        abort(500) #NOTE: Add custom DB error wrapper for app.errorhandler()
    
    pyReadableResult : list = [row._asdict() for row in qResult]

    return jsonify({"result" : pyReadableResult}), 200

#Transcriptions and Translations
@app.route("/transcript", methods = ["GET"])
def transcript():
    return render_template("transcript.html")

@app.route("/translate", methods = ["GET"])
def translate():
    return render_template("translate.html")

@app.route("/transcript-speech", methods = ["POST"])
def transcript_speech():
    audio_file = request.files.get("audio-file", None)
    if audio_file is None:
        raise Unexpected_Request_Format("Audio File Not Found in Request Object\nAt:POST /transcript-speech")
    
    starting_time = time.time()
    #Add file validation logic here
    #Saving file
    filepath : str = os.path.join(app.config["UPLOAD_FOLDER"], audio_file.filename)
    audio_file.save(filepath)

    #Transcripting audio
    print(filepath)
    result = getAudioTranscription(filepath)
    time_taken = starting_time - time.time()

    try:
        db.session.execute(insert(Transcription_Request)
                           .values(requested_by=g.decodedToken["sub"],
                                   language="en",
                                   transcripted_text=result["text"],
                                   time_requested=starting_time))
        db.session.execute(update(User)
                           .where(User.id == g.decodedToken["sub"])
                           .values(transcriptions=User.transcriptions + 1))
        db.session.commit()
    except (IntegrityError, DataError, ValueError):
        db.session.rollback()
        abort(500)
    
    return jsonify({"text" : result["text"], "confidence" : result["confidence"], "time" : time_taken}), 200

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
        if src_language is not None and src_language not in AVAILABLE_LANGUAGES and src_language != "auto":
            return jsonify({"error" : "Source Language Not Found"}), 404

        #Initialize Translation Process
        start_time = time.time()
        translator = Translator()

        translation_metadata = translator.translate(text = original_text, dest = dest_language, src = src_language or 'auto')

        translated_text, translation_src = translation_metadata.text, translation_metadata.src
        time_taken = time.time() - start_time
        try:
            db.session.execute(insert(Translation_Request)
                               .values(requested_by=g.decodedToken["sub"],
                                        language_from=translation_src,
                                        language_to=dest_language,
                                        requested_text=original_text,
                                        translated_text=translated_text))
            db.session.execute(update(User)
                               .where(User.id == g.decodedToken["sub"])
                               .values(translations = User.translations + 1))
            db.session.commit()
        except (IntegrityError, DataError, StatementError):
            db.session.rollback()
            abort(500)

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