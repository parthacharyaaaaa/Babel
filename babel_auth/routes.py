from babel_auth import auth, tokenManager
from flask import request, abort, jsonify, Response
from werkzeug.exceptions import BadRequest
from datetime import datetime

@auth.route("/login", methods = ["POST"])
def login():
    if not request.is_json:
        raise BadRequest()
    authentication_data = request.get_json()
    if not ("identity" in authentication_data and "password" in authentication_data):
        raise BadRequest()
    
    aToken = tokenManager.issueAccessToken()
    rToken = tokenManager.issueRefreshToken(familyID=1)

    response = jsonify({
        "access" : aToken,
        "refresh" : rToken,
        "time_of_issuance" : datetime.now(),
        "issuer" : "babel-auth-service"
    })

    return response, 201

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

@auth.route("/purge-family", methods = ["GET"])
def purgeFamily():
    familyID = request.headers.get("Refresh", request.headers.get("refresh"))
    if not familyID:
        raise BadRequest(f"Invalid Refresh Token provided to [{request.method}] {request.url_rule}")
    
    tokenManager.invalidateFamily(familyID)
    response : Response = jsonify({"message" : "Token Revoked"})
    response.headers["iss"] = "babel-auth-service"

    return response, 204

@auth.route("/ip-blacklist", methods = ["POST"])
def blacklist():
    ...