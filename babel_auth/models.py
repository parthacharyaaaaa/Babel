from babel_auth import db
from sqlalchemy import CheckConstraint

class Token(db.Model):
    __tablename__ = "tokens"
    # JWT Metadata
    jit = db.Column(db.String(16), primary_key = True, unique = True, nullable = True)
    sub = db.Column(db.Integer, unique = False, nullable = False)
    iat = db.Column(db.Integer, unique = False, nullable = False)
    exp = db.Column(db.Integer, unique = False, nullable = False)
    ipa = db.Column(db.String(15), unique = False, nullable = True)

    # Rotational Metadata
    revoked = db.Column(db.Boolean, unique = False, nullable = True, default = False)
    family_id = db.Column(db.Integer, unique = False, nullable = False, index = True)

    def __repr__(self) -> str:
        return f"<Refresh Token(jit={self.jit}, sub={self.sub}, exp={self.exp}, ipa={self.ipa}). Revoked: {self.revoked}, family_id: {self.family_id}>"
    
    __table__args__ = (
        CheckConstraint("iat < exp", name = "check_iat_less_than_exp"),
    )
