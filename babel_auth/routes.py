from babel_auth import auth, db, tokenManager
from flask import request, abort, jsonify

@auth.route("/login", methods = ["POST"])
def login():
    return jsonify("bitches ain't shit but hoes and tricks"), 200

@auth.route("/signup", methods = ["POST"])
def signup():
    ...

@auth.route("/logout", methods = ["POST"])
def logout():
    ...

@auth.route("/delete-account", methods = ["DELETE"])
def deleteAccount():
    ...

@auth.route("/reissue", methods = ["POST"])
def reissue():
    authMetadata = request.headers.get("Authorization", request.headers.get("authorization", None))

    if not authMetadata:
        raise KeyError()
    
    refreshToken = tokenManager.decodeToken(token=authMetadata,
                                             checkAdditionals=False,
                                             tType="refresh")
    
    nAccessToken, nRefreshToken = tokenManager.reissueTokenPair(refreshToken)
    return jsonify({"access" : nAccessToken, "refresh" : nRefreshToken}), 201


@auth.route("/ip-blacklist", methods = ["POST"])
def blacklist():
    ...
