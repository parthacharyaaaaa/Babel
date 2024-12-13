from babel_auth import auth, tokenManager
from flask import request, abort, jsonify, Response
from werkzeug.exceptions import BadRequest
from datetime import datetime
import requests
import os

### Error Handlers ###
@auth.errorhandler(ValueError)
@auth.errorhandler(BadRequest)
def badRequest(e):
    message = "Bad Request: Check message format!" if not hasattr(e, "description") else e.description
    rBody = {"message" : message}
    if hasattr(e, "_additional_info"):
        rBody.update({"additional details" : e._additional_info})

    response = jsonify(rBody)
    response.headers.update({"issuer" : "babel-auth-service"})

    return response, 400

@auth.route("/authenticate", methods = ["POST"])
def authenticate():
    if not request.is_json:
        raise BadRequest()
    authentication_data = request.get_json(force=True, silent=False)
    if not ("identity" in authentication_data and "password" in authentication_data):
        raise BadRequest()
    
    valid = requests.post(f"{auth.config['PROTOCOL']}://{auth.config['RESOURCE_SERVER_ORIGIN']}/validate-user",
                          json = {"identity" : authentication_data["identity"], "password" : authentication_data["password"]},
                          headers={"AUTH-API-KEY" : os.environ["AUTH_API_KEY"]})
    
    if valid.status_code != 200:
        return jsonify({"message" : "Authentication Failed",
                        "response_message" : valid.json().get("message", "None")}), valid.status_code
    
    subject = valid.json()["sub"]
    aToken = tokenManager.issueAccessToken(sub = subject)
    rToken = tokenManager.issueRefreshToken(sub = subject,
                                            familyID = tokenManager.generate_unique_identifier())

    response = jsonify({
        "access" : aToken,
        "refresh" : rToken,
        "time_of_issuance" : datetime.now(),
        "issuer" : "babel-auth-service"
    })

    return response, 201

@auth.route("/register", methods = ["POST"])
def register():
    if not request.is_json:
        raise BadRequest("Only JSON mimetype accepted by POST /register")
    
    registrationDetails : dict = request.get_json(force=True, silent=False)
    
    if not ("username" in registrationDetails and
            "email" in registrationDetails and
            "password" in registrationDetails and
            "cpassword" in registrationDetails):
        raise BadRequest("Mandatory field missing")
    
    if registrationDetails["password"] != registrationDetails["cpassword"]:
        raise BadRequest("Passwords do not match")
    
    registrationDetails.update({"authprovider" : "babel-auth"})
    valid = requests.post(f"{auth.config['PROTOCOL']}://{auth.config['RESOURCE_SERVER_ORIGIN']}/register",
                          json = registrationDetails,
                          headers={"AUTH-API-KEY" : os.environ["AUTH_API_KEY"]})
    
    if valid.status_code != 200:
        return jsonify({"message" : "Failed to create account",
                        "response_message" : valid.json().get("message", "Sowwy >:3")}), valid.status_code
    
    subject = valid.json()["sub"]
    aToken = tokenManager.issueAccessToken(sub = subject)
    rToken = tokenManager.issueRefreshToken(sub = subject,
                                            familyID = tokenManager.generate_unique_identifier())

    response = jsonify({
        "access" : aToken,
        "refresh" : rToken,
        "time_of_issuance" : datetime.now(),
        "issuer" : "babel-auth-service"
    })

    return response, 201

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
    '''
    Purges an entire token family in case of a reuse attack or a normal client logout
    '''
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
