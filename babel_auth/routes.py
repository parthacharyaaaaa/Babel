from babel_auth import auth, tokenManager
from flask import request, abort, jsonify, Response
from werkzeug.exceptions import BadRequestKeyError

@auth.route("/login", methods = ["POST"])
def login():
    return jsonify("bitches ain't shit but hoes and tricks"), 200

@auth.route("/signup", methods = ["POST"])
def signup():
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

@auth.route("/revoke", methods = ["GET"])
def revoke():
    print(request.authorization)
    familyID = request.headers.get("Authorization").split()[-1]
    if not familyID:
        raise BadRequestKeyError("Revokation requires refresh token to be given")
    
    tokenManager.invalidateFamily(request.headers.get("Authorization")["fid"])
    response : Response = jsonify({"message" : "Token Revoked"})
    response.headers["iss"] = "babel-auth-service"

    return response, 204

@auth.route("/ip-blacklist", methods = ["POST"])
def blacklist():
    ...