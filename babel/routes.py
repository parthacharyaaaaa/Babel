from flask import jsonify, request, abort, g
import time
from babel import app, db, bcrypt, RedisManager, ErrorLogger
from babel.models import *
from babel.config import *
from auxillary_packages.errors import *
from werkzeug.exceptions import Unauthorized, InternalServerError, HTTPException, Forbidden, NotFound, MethodNotAllowed
from babel.transciber import getAudioTranscription
from googletrans import Translator
from sqlalchemy import select, insert, update, delete
from sqlalchemy.sql import literal
from sqlalchemy.exc import IntegrityError, DataError, StatementError, SQLAlchemyError, CompileError
from auxillary_packages.decorators import *
import jwt
import requests
import orjson
import zlib
import traceback
LANG_CACHE = None
FILTER_PREFERENCES = {0 : "all", 1 : "translate", 2 : "transcribe"}

@app.after_request
def afterRequest(response):
    response.headers["Content-Security-Policy"] = app.config["CSP_STRING"] + f" connect-src 'self' {os.environ['AUTH_SERVER_ADDRESS']};"
    print(response.headers)
    return response

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
    print(e.__class__)
    print(traceback.format_exc())
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

    userRecord : User = db.session.execute(select(User).where(User.username == uname)).scalar_one_or_none()
    print(userRecord)
    emailRecord : User = db.session.execute(select(User).where(User.email_id == email)).scalar_one_or_none()
    print(emailRecord)

    if emailRecord and not emailRecord.deleted:
        return jsonify({"message" : "This email address is already registered, please log in or use a different email address"}), 409

    if userRecord and not userRecord.deleted:
        return jsonify({"message" : "This username is already registered, please log in or use a different username"}), 409
    
    try:
        # Email and username exist in a single deleted account
        single_duplication = (userRecord and not emailRecord) or (emailRecord and not userRecord) or (emailRecord and userRecord and emailRecord.id == userRecord.id)

        # Credentials duplicated on 2 deleted accounts, one has email, other has username
        double_duplication = userRecord and emailRecord and userRecord.id != emailRecord.id
        print(single_duplication, double_duplication)
        if single_duplication:
            # Effectively restore the account
            db.session.execute(update(User).where(User.id == userRecord.id).values(username = uname,
                                                password = bcrypt.generate_password_hash(password),
                                                email_id = email,
                                                time_created = datetime.now(),
                                                last_login = datetime.now(),
                                                deleted = False,
                                                time_deleted = None,
                                                transcriptions = 0,
                                                translations = 0))
        elif double_duplication:
            # Restore the account that was deleted recently and purge the older deleted account, poor dude
            purgeID = userRecord.id if userRecord.time_deleted > emailRecord.time_deleted else emailRecord.id
            restoreID = userRecord.id if purgeID != userRecord.id else emailRecord.id
            db.session.execute(delete(User).where(User.id == purgeID))  #RIP
            
            db.session.execute(update(User).where(User.id == restoreID).values(username = uname,
                                                password = bcrypt.generate_password_hash(password),
                                                email_id = email,
                                                time_created = datetime.now(),
                                                last_login = datetime.now(),
                                                deleted = False,
                                                time_deleted = None,
                                                transcriptions = 0,
                                                translations = 0))
        else:
            # No duplications whatsoever, we good
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
            user = db.session.execute(select(User).where(User.email_id == identity, User.deleted == False)).scalar_one_or_none()
        else:
            user = db.session.execute(select(User).where(User.username == identity, User.deleted == False)).scalar_one_or_none()

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
    rToken = request.cookies.get("refresh", request.cookies.get("Refresh"))
    if not rToken:
        raise BadRequest(f"POST /{request.path[1:]} requires a refresh token to allow account deletion. Please reauthenticate yourself and then repeat the deletion process. If this issue persists, contact support")
    
    decodedRToken = jwt.decode(rToken,
                               key=os.environ["SIGNING_KEY"],
                               algorithms=["HS256"],
                               leeway=timedelta(minutes=3),
                               options={"verify_nbf" : False})
    
    password : str = request.get_json(force=True)["password"]
    if not password:
        raise BadRequest(f"POST /{request.path[1:]} Password missing")
    
    try:
        uPass = db.session.execute(select(User.password).where(User.username == g.decodedToken["sub"])).scalar_one_or_none()
        if not bcrypt.check_password_hash(uPass, password):
            raise Unauthorized("Incorrect password")

        db.session.execute(update(User)
                           .where(User.username == g.decodedToken["sub"])
                           .values(deleted = True, time_deleted = datetime.now()))
        db.session.commit()
    except (DataError, StatementError):
        db.session.rollback()
        abort(500)

    requests.delete(url=f"{app.config['AUTH_COMMUNICATION_PROTOCOL']}://{app.config['AUTH_SERVER_ORIGIN']}/delete-account",
                headers={"refreshID" : decodedRToken["fid"], "AUTH-API-KEY" : os.environ["AUTH_API_KEY"]})
    return jsonify({"message" : "Account Deleted Successfully"}), 204

@app.route("/fetch-history", methods = ["GET"])
@token_required
def fetch_history():
    username : str = g.decodedToken.get("sub", None)
    try:
        filterPreference : int = int(request.args.get("filter", 0))
    except:
        filterPreference = 0
    try:
        sortPreference : int = int(request.args.get("sort", 0))
    except:
        sortPreference = 0

    try:
        currentPage : int = int(request.args.get("page", 1))
    except ValueError:
        raise BadRequest(f"POST /{request.path[1:]} Requires an integer to indicate value result")
    
    cached_result = RedisManager.get(f"uh:{username}:{filterPreference}_{sortPreference}_{currentPage}")
    if cached_result:
        return jsonify(orjson.loads(cached_result))

    perPage : int = 10 + 1

    transcriptionQuery =(select(Transcription_Request.id,
                                Transcription_Request.time_requested.label("time_requested"),
                                Transcription_Request.transcripted_text.label("content"),
                                Transcription_Request.language.label("lang"),
                                literal("transcription").label("type"),
                                literal(None).label("src"),
                                literal(None).label("dst"),
                                ).where(Transcription_Request.requested_by == username))

    translationQuery = (select(Translation_Request.id,
                              Translation_Request.time_requested.label("time_requested"),
                              Translation_Request.translated_text.label("content"),
                              literal(None).label("lang"),
                              literal("translation").label("type"),
                              Translation_Request.language_from.label("src"),
                              Translation_Request.language_to.label("dst"),
                              ).where(Translation_Request.requested_by == username))

    combinedQuery = (transcriptionQuery.union_all(translationQuery)
                    .order_by(db.desc("time_requested") if sortPreference == 0 else db.asc("time_requested"))
                    .limit(perPage)
                    .offset((currentPage - 1) * perPage))
    try:
        if filterPreference == 2:
            qResult = db.session.execute(transcriptionQuery.order_by(Transcription_Request.time_requested.desc() if sortPreference == 0 else Transcription_Request.time_requested.asc()).limit(perPage).offset((currentPage -1) * perPage))
        elif filterPreference == 1:
            qResult = db.session.execute(translationQuery.order_by(Translation_Request.time_requested.desc() if sortPreference == 0 else Translation_Request.time_requested.asc()).limit(perPage).offset((currentPage -1) * perPage))
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
        RedisManager.setex(f"uh:{username}:{filterPreference}_{sortPreference}_{currentPage}", 120, orjson.dumps(pyReadableResult))

    resposne = jsonify(pyReadableResult[:-1])
    if len(pyReadableResult) < perPage:
        resposne.headers["exhausted"] = True
    return resposne, 200

@app.route("/transcript-speech", methods = ["POST"])
@enforce_mimetype("form-data")
@token_required
def transcript_speech():
    audio_file = request.files.get("audio-file", None)
    if audio_file is None:
        raise BadRequest("Audio File Not Found in Request Object\nAt:POST /transcript-speech")
    
    if audio_file.content_length and audio_file.content_type > 25*1024*1024:
        raise BadRequest("Very large file, cannot process!")
    
    starting_time = time.time()
    #Saving file
    filepath : str = os.path.join(app.config["UPLOAD_FOLDER"], audio_file.filename)
    audio_file.save(filepath)

    if os.path.getsize(filepath) > 25*1024*1024:
        os.remove(filepath)
        raise BadRequest("Very large file, cannot process!")

    result = getAudioTranscription(filepath)
    time_taken = starting_time - time.time()
    try:
        db.session.execute(insert(Transcription_Request)
                           .values(requested_by=g.decodedToken["sub"],
                                   language="en",
                                   transcripted_text=result["text"],
                                   time_requested=datetime.fromtimestamp(starting_time)))
        db.session.execute(update(User)
                           .where(User.id == g.decodedToken["sub"], User.deleted == False)
                           .values(transcriptions=User.transcriptions + 1))
        db.session.commit()
    except (IntegrityError, DataError, ValueError, CompileError):
        db.session.rollback()
        abort(500)
    return jsonify({"text" : result["text"], "confidence" : result["confidence"], "time" : time_taken}), 200

@app.route("/translate-text", methods = ["POST"])
@enforce_mimetype("JSON")
@token_required
def translate_text():
    try:
        translation_request = request.get_json(force=True, silent=False)
        if request.content_length and request.content_length > 8192:
            return BadRequest("Maximum request size exceeded")

        original_text : str = translation_request["text"]
        dest_language : str = translation_request["dest"].lower()
        src_language : str = translation_request.get("src", None)
        src_language = None if src_language.strip() == "" else src_language.lower()

        cached_result = RedisManager.get("TL:" + str(zlib.adler32(f"{g.decodedToken['sub']}:{src_language}-{dest_language}-{original_text}".encode())))
        if cached_result:
            return jsonify(orjson.dumps(cached_result)), 200

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
                               .where(User.username == g.decodedToken["sub"], User.deleted == False)
                               .values(translations = User.translations + 1))
            db.session.commit()
        except (IntegrityError, DataError, StatementError):
            db.session.rollback()
            abort(500)


        RedisManager.setex("TL:" + str(zlib.adler32(f"{g.decodedToken['sub']}:{src_language}-{dest_language}-{original_text}".encode())),
                           120,
                           orjson.dumps({"translated-text" : translated_text, "src" : translation_src, "time" : time_taken}))
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