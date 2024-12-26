from jwt import decode, PyJWTError, ExpiredSignatureError
from flask import request, g, make_response
import os
from werkzeug.exceptions import Unauthorized, BadRequest
from datetime import timedelta
import functools

def token_required(endpoint):
    '''
    Protect an endpoint by validating an access token. Requires the header "Authorization: Bearer <credentials>". 
    Furthermore, sets global data (flask.g : _AppCtxGlobals) for usage of token details in the decorated endpoint
    '''
    @functools.wraps(endpoint)
    def decorated(*args, **kwargs):
        try:
            auth_metadata = request.cookies.get("access", request.cookies.get("Access"))
            if not auth_metadata:
                raise Unauthorized("Authentication details missing")
            decodedToken = decode(
                                jwt=auth_metadata.split()[-1],
                                key=os.environ["SIGNING_KEY"],
                                algorithms=["HS256"],
                                issuer="babel-auth-service",
                                leeway=timedelta(minutes=3)
            )
            g.decodedToken = decodedToken
        except KeyError as e:
            raise BadRequest(f"Endpoint /{request.path[1:]} requires an authorization token to give access to resource")
        except ExpiredSignatureError:
            raise Unauthorized("JWT token expired, begin refresh issuance")
        except PyJWTError as e:
            raise Unauthorized("JWT token invalid")
        
        return endpoint(*args, **kwargs)
    return decorated

def private(endpoint):
    @functools.wraps(endpoint)
    def decorated(*args, **kwargs):
        if request.headers.get("AUTH-API-KEY") != os.environ.get("AUTH_API_KEY", -1):
               raise Unauthorized("Access Denied >:(")
        return endpoint(*args, **kwargs)
    return decorated

def enforce_mimetype(mimetype : str):
    def inner_dec(endpoint):
        @functools.wraps(endpoint)
        def decorated(*args, **kwargs):
            if not request.mimetype or request.mimetype.split("/")[-1] != mimetype.lower():
                e = BadRequest(f"Invalid mimetype forwarded to {request.method.upper()} /{request.root_path}")
                e.__setattr__("_additional_info", f"Expected mimetype: {mimetype}, received {request.mimetype} instead")
                raise e
            return endpoint(*args, **kwargs)
        return decorated
    return inner_dec

def attach_CORS_headers(endpoint):
    @functools.wraps(endpoint)
    def decorated(*args, **kwargs):
        try:
            if request.method == "OPTIONS":
                print("Options")
                response = make_response()  # Create a response for OPTIONS
                response.headers["Access-Control-Allow-Origin"] = "http://192.168.0.105:5000"
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, DELETE, PUT"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, sub, X-CSRF-TOKEN"
                return response  # Return the OPTIONS response immediately

            result = endpoint(*args, **kwargs)
            response = result[0]
            response.headers["Access-Control-Allow-Origin"] = "http://192.168.0.105:5000"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, DELETE, PUT"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, sub, X-CSRF-TOKEN"
            return response, result[1]
        except Exception as e:
            raise e
    return decorated