from babel import db
from flask_login import UserMixin
from sqlalchemy import Constraint, Index, ForeignKey
from datetime import datetime

class User(db.Model, UserMixin):
    __tablename__ = "users"

    #Credentials Metadata
    id = db.Column(db.Integer, primary_key = True, nullable = False)
    username = db.Column(db.String(64), nullable = False, unique = True)
    password = db.Column(db.String(264), nullable = False)
    email_id = db.Column(db.String(64), nullable = False, index = True, unique = True)

    #Creation Metadata
    time_created = db.Column(db.DateTime, nullable = False)
    last_login = db.Column(db.DateTime, nullable = False)
    deleted = db.Column(db.Boolean, nullable = False, default = True)
    time_deleted = db.Column(db.DateTime, nullable = True)

    #Usage Metadata
    transcriptions = db.Column(db.Integer, nullable = False, default = 0)
    translations = db.Column(db.Integer, nullable = False, default = 0)

    def __init__(self, username : str, password : str, email : str) -> None:
        #Call param checker before initialization
        self.username = username
        self.password = password
        self.time_created = datetime.now()
        self.last_login = datetime.now()
        self.transcriptions = 0
        self.translations = 0
    
    def __repr__(self) -> str:
        return f"<User Object {self.id}: Username - {self.username}>"
    
    def format_to_dict(self) -> dict:
        return {"username" : self.username,
                "time_created" : self.time_created,
                "last_login" : self.last_login,
                "transcriptions" : self.transcriptions,
                "translations" : self.translations}
    
class Translation_Request(db.Model):
    __tablename__ = "translations"

    #Main Metadata
    id = db.Column(db.Integer, primary_key = True, nullable = False)
    requested_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable = False)
    language_from = db.Column(db.String(16), nullable = False)
    language_to = db.Column(db.String(16), nullable = False)
    requested_text = db.Column(db.String(512), nullable = False)
    translated_text = db.Column(db.Text, nullable = False)

    #Time Metadata
    time_requested = db.Column(db.DateTime, nullable = False)

    def __init__(self, language_from : str, language_to : str, requsted : str, translated : str, time_requested : datetime) -> None:
        self.language_from = language_from
        self.language_to = language_to
        self.requested_text = requsted
        self.translated_text = translated
        self.time_requested = time_requested or datetime.now()
    
    def __repr__(self) -> str:
        return f"<Translation_Request {self.id}>"
    
    def format_to_dict(self) -> dict:
        return {"id" : self.id,
                "user" : self.requested_by,
                "original_language" : self.language_from,
                "translated_language" : self.language_to,
                "time_requested" : self.time_requested
                }

class Transcription_Request(db.Model):
    __tablename__ = "transcriptions"

    #Main Metadata
    id = db.Column(db.Integer, primary_key = True, nullable = False)
    requestor = db.Column(db.Integer, db.ForeignKey("users.id"), nullable = False)
    language = db.Column(db.String(16), nullable = False, default = "Eng")
    transcipted_text = db.Column(db.Text, nullable = False)

    #Time Metadata
    time_requested = db.Column(db.DateTime, nullable = False)

    def __init__(self, language_from : str, language_to : str, requsted : str, transcripted : str, time_requested : datetime) -> None:
        self.language_from = language_from
        self.language_to = language_to
        self.requested_text = requsted
        self.transcripted_text = transcripted
        self.time_requested = time_requested or datetime.now()

    def __repr__(self) -> str:
        return f"<Transcription_Request {self.id}>"
    
    def format_to_dict(self) -> dict:
        return {"id" : self.id,
                "user": self.requestor,
                "language" : self.language, 
                "time_requested" : self.time_requested}
    
class Error_Log(db.Model):
    __tablename__ = "error_logs"

    id = db.Column(db.Integer, primary_key = True, nullable = False, unique = True)
    victim_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable = False)
    error_code = db.Column(db.Integer, nullable = False)
    resolved = db.Column(db.Boolean, nullable = False, default = False)

    time = db.Column(db.DateTime, nullable = False)
    
    def __init__(self, victim_id : int, error_code : int) -> None:
        self.victim_id = victim_id
        self.error_code = error_code
        self.time = datetime.now()

    def __repr__(self) -> str:
        return f"<Error_Log {self.id}>"
    
    def format_to_dict(self) -> dict:
        return {"id" : self.id,
                "error_code" : self.error_code,
                "victim" : self.victim_id,
                "time_of_error" : self.time,
                "resolved?" : self.resolved}