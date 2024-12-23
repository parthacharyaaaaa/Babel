from flask import jsonify, request, abort, g
import time
from babel import app, db, bcrypt, RedisManager, ErrorLogger
from babel.models import *
from babel.config import *
from auxillary_packages.errors import *
from werkzeug.exceptions import Unauthorized, FailedDependency, InternalServerError, HTTPException, Forbidden, NotFound, MethodNotAllowed
from babel.transciber import getAudioTranscription
from googletrans import Translator
from sqlalchemy import select, insert, update
from sqlalchemy.sql import literal
from sqlalchemy.exc import IntegrityError, DataError, StatementError, SQLAlchemyError
from auxillary_packages.decorators import *
import requests
import orjson

LANG_CACHE = None

### Error Handlers ###
@app.errorhandler(MethodNotAllowed)
def methodNotAllowed(e : MethodNotAllowed):
    response = {"message" : f"{getattr(e, 'description', 'Method Not Allowed')}"}
    if hasattr(e, "HTTP_type") and hasattr(e, "expected_HTTP_type"):
        response.update({"additional" : f"Expected {e.expected_HTTP_type}, got {e.HTTP_type}"})
    return jsonify(response), 405

@app.errorhandler(NotFound)
def resource_not_found(e : NotFound):
    return jsonify({"message": "Requested resource could not be found."}), 404

@app.errorhandler(Forbidden)
@app.errorhandler(Unauthorized)
def forbidden(e : Forbidden | Unauthorized):
    response = jsonify({"message" : getattr(e, "description", "Resource Access Denied")})
    response.headers.update({"issuer" : "babel-auth-flow"})
    return response, 403

@app.errorhandler(BadRequest)
@app.errorhandler(KeyError)         #NOTE: Very important to set KeyError.description here, instead of KeyError.message
def unexpected_request_format(e : BadRequest | KeyError):
    rBody = {"message" : getattr(e, "description", "Bad Request! Ensure proper request format")}
    if hasattr(e, "_additional_info"):
        rBody.update({"additional information" : e._additional_info})
    response = jsonify(rBody)
    return response, 400

@app.errorhandler(DISCRETE_DB_ERROR)
def discrete_db_err(e : DISCRETE_DB_ERROR):
    ErrorLogger.addEntryToQueue(e)
    r = jsonify({"message" : getattr(e, "description", "DB_ERR_500")})
    r.headers.update({"Issuer" : "Babel-Backend-Services"})
    return r, 500

@app.errorhandler(Exception)
@app.errorhandler(HTTPException)
@app.errorhandler(InternalServerError)
def internalServerError(e : Exception):
    ErrorLogger.addEntryToQueue(e)
    return jsonify({"message" : getattr(e, "description", "An Error Occured"), "Additional Info" : getattr(e, "_additional_info", "There seems to be an issue with our service, please retry after some time or contact support")}), 500

### Endpoints ###
@app.route("/register", methods = ["POST"])
@private
@enforce_mimetype("JSON")
def register():
    registrationDetails = request.get_json(force=True, silent=False)
    try:
        uname : str = registrationDetails["username"].strip()
        email : str = registrationDetails["email"].strip()
        password : str = registrationDetails["password"]

    except KeyError as k:
        raise BadRequest(f"POST /{request.path[1:]} Mandatory field missing")

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
    
    return jsonify({"message" : "Account Registered Successfully", "sub" : uname}), 201

@app.route("/validate-user", methods = ["POST"])
@private
@enforce_mimetype("JSON")
def validateUser():
    try:
        userMetadata = request.get_json(force=True, silent=False)
        identity = userMetadata["identity"]
        password = userMetadata["password"]
        if "@" in identity:
            user = db.session.execute(select(User).where(User.email_id == identity)).scalar_one_or_none()
        else:
            user = db.session.execute(select(User).where(User.username == identity)).scalar_one_or_none()

        if not user:
            return jsonify({"message":"User does not exist"}), 404
        
        if not bcrypt.check_password_hash(pw_hash=user.password,
                                          password=password):
            return jsonify({"message" : "Incorrect username or password"}), 401
        
        return jsonify({"message" : "User Authenticated", "sub" : user.username}), 200
    except KeyError:
        raise BadRequest(f"{request.method} /{request.root_path} expects mandatory fields: identity, password")

@app.route("/users/<string:name>", methods = ["GET"])
def getUser(name):
    cached_result = RedisManager.get(f"user:{name}")
    if cached_result:
        return jsonify(orjson.loads(cached_result)), 200

    try:
        user = db.session.execute(select(User).where(User.username == name)).scalar_one_or_none()
    except:
        raise InternalServerError("An error occured in fetching user data")

    if not user:
        return jsonify({"message" : "User not found",
                        "additional info" : "Make sure the name is spelt right, and that a user with the given username exists"}), 404

    result = user.format_to_dict()
    RedisManager.setex(f"user:{name}", 90, orjson.dumps(result))
    return jsonify(result), 200

@app.route("/delete-account", methods = ["DELETE"])
@enforce_mimetype("JSON")
@token_required
def delete_account():
    password : str = request.get_json(force=True)["password"]
    if not password:
        raise BadRequest(f"POST /{request.path[1:]} Password missing")
    try:
        db.session.execute(update(User)
                           .where(User.username == g.decodedToken["sub"])
                           .values(deleted = True, time_deleted = datetime.now()))
        db.session.commit()
    except (DataError, StatementError):
        db.session.rollback()
        abort(500)

    # Logic for sending an API request to auth server to instantly delete all assosciated refresh tokens
    requests.get(url=f"{app.config['AUTH_COMMUNICATION_PROTOCOL']}://{app.config['AUTH_SERVER_ORIGIN']}/purge-family",
                headers={"Refresh" : g.decodedToken["fid"]})
    
    return jsonify({"message" : "Account Deleted Successfully"}), 200

@app.route("/fetch-history", methods = ["GET"])
@token_required
def fetch_history():
    username : str = g.decodedToken.get("sub", None)

    viewPreference : str = request.args.get("preference", "all")
    try:
        currentPage : int = int(request.args.get("page", 1))
    except ValueError:
        raise BadRequest(f"POST /{request.path[1:]} Requires an integer to indicate value result")
    
    cached_result = RedisManager.get(f"u_hist:{username}:{viewPreference}")
    if cached_result:
        return jsonify({"result" : orjson.loads(cached_result)})

    perPage : int = 10

    transcriptionQuery =(select(Transcription_Request.id,
                                Transcription_Request.time_requested.label("time_requested"),
                                Transcription_Request.transcipted_text.label("content"),
                                Transcription_Request.language.label("lang"),
                                literal(None).label("src"),
                                literal(None).label("dst"),
                                ).where(Transcription_Request.requested_by == username))

    translationQuery = (select(Translation_Request.id,
                              Translation_Request.time_requested.label("time_requested"),
                              Translation_Request.translated_text.label("content"),
                              literal(None).label("lang"),
                              Translation_Request.language_from.label("src"),
                              Translation_Request.language_to.label("dst"),
                              ).where(Translation_Request.requested_by == username))

    combinedQuery = (transcriptionQuery.union_all(translationQuery)
                    .order_by(db.desc("time_requested"))
                    .limit(perPage)
                    .offset((currentPage - 1) * perPage))
    
    try:
        if viewPreference == "transcription":
            qResult = db.session.execute(transcriptionQuery.order_by(Transcription_Request.time_requested.desc()).limit(perPage).offset((currentPage -1) * perPage))
        elif viewPreference == "translation":
            qResult = db.session.execute(translationQuery.order_by(Translation_Request.time_requested.desc()).limit(perPage).offset((currentPage -1) * perPage))
        else:
            qResult = db.session.execute(combinedQuery)
    except (IntegrityError, DataError) as e:
        e = SQLAlchemyError
        e.__setattr__("description", "Seems to be an error with our database service. Please try again later, or contact support")
        e.__setattr__("_additional_info", f"{e.__class__}, {e.with_traceback()}. Time: {datetime.now()}")
        raise e
    except Exception as e:
        raise DISCRETE_DB_ERROR()
    
    pyReadableResult : list = [row._asdict() for row in qResult]

    if currentPage <= 3:
        RedisManager.setex(f"u_hist:{username}:{viewPreference}", 120, orjson.dumps(pyReadableResult))
    return jsonify({"result" : pyReadableResult}), 200

@app.route("/transcript-speech", methods = ["POST"])
@enforce_mimetype("form-data")
@token_required
def transcript_speech():
    audio_file = request.files.get("audio-file", None)
    if audio_file is None:
        raise BadRequest("Audio File Not Found in Request Object\nAt:POST /transcript-speech")
    
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
@enforce_mimetype("JSON")
@token_required
def translate_text():
    try:
        translation_request = request.get_json(force=True, silent=False)

        original_text : str = translation_request["text"]
        dest_language : str = translation_request["dest"].lower()
        src_language : str = translation_request.get("src", None)
        src_language = None if src_language.strip() == "" else src_language.lower()

        #Validating strings
        if original_text.strip() == "" or dest_language.strip() == "":
            raise ValueError()

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
                                        translated_text=translated_text,
                                        time_requested=datetime.fromtimestamp(start_time))
                                )
            db.session.execute(update(User)
                               .where(User.username == g.decodedToken["sub"])
                               .values(translations = User.translations + 1))
            db.session.commit()
        except (IntegrityError, DataError, StatementError):
            db.session.rollback()
            abort(500)
        return jsonify({"translated-text" : translated_text, "src" : translation_src, "time" : time_taken}), 200

    except BadRequest as e:
        print("NOT JSON")
        return jsonify({"error" : "yeah yeah"}), 400
    except KeyError as e:
        print("JSON NOT PROPER KWARGS")
        return jsonify("Invalid Request"), 400

@app.route("/fetch-languages", methods = ["GET"])
def fetch_languages():
    global LANG_CACHE
    if LANG_CACHE:
        return jsonify(LANG_CACHE), 200

    available_languages = {"auto" : "auto-detect"}
    available_languages.update(AVAILABLE_LANGUAGES)

    LANG_CACHE = available_languages

    return jsonify(available_languages), 200