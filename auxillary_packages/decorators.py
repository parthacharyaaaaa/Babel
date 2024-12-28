from jwt import decode, PyJWTError, ExpiredSignatureError
from flask import request, g, make_response, Response, jsonify, current_app
import os
from werkzeug.exceptions import Unauthorized, BadRequest, InternalServerError
from datetime import timedelta
import functools
import secrets, random

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
        try:
            # IP check
            request_ip = request.headers.get("X-FORWARDED-FOR", request.remote_addr)
            if request_ip not in current_app.config["PRIVATE_IP_ADDRS"]:
                raise Unauthorized()
            
            # HTTP check
            if request.headers["PRIVATE-API-KEY"] != current_app.config["PRIVATE_COMM_KEYS"]:
               raise Unauthorized("Access Denied >:(")
            
        except KeyError:
               if not request.headers.get("PRIVATE-API-KEY"):
                   raise Unauthorized("Private endpoint, requires an API key")
               else:
                   raise InternalServerError()
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
                response = jsonify()
                response.headers["Access-Control-Allow-Origin"] = "http://192.168.0.105:5000"
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, DELETE, PUT"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, sub, X-CSRF-TOKEN, X-CLIENT-TYPE"
                response.headers["Access-Control-Expose-Headers"] = "Authorization, Content-Type, sub, X-CSRF-TOKEN, X-CLIENT-TYPE"
                return response, 204

            result = endpoint(*args, **kwargs)
            if isinstance(result, tuple):
                response = result[0]
                code = result[1]
            else:
                response = result
                code = 200
            response.headers["Access-Control-Allow-Origin"] = "http://192.168.0.105:5000"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, DELETE, PUT"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, sub, X-CSRF-TOKEN, X-CLIENT-TYPE"
            response.headers["Access-Control-Expose-Headers"] = "Authorization, Content-Type, sub, X-CSRF-TOKEN, X-CLIENT-TYPE"

            return response, code
        except Exception as e:
            print(e.__class__)
            raise e
    return decorated

def CSRF_protect(endpoint):
    @functools.wraps(endpoint)
    def decorated(*args, **kwargs):
        clientType = request.headers.get("X-CLIENT-TYPE")
        if not clientType:
            clientType = "web" # Safe assumption, at least for GET
        elif clientType not in ["web", "mobile", "api", "handheld", "test"]:
            raise BadRequest("Invalid Client Type")
    
        if clientType == "web":
            yin_token = request.headers.get("X-CSRF-TOKEN")
            yang_token = request.cookies.get("X-CSRF-TOKEN")

            if yin_token == "null":
                yin_token = None
            if yang_token == "null":
                yang_token = None

            if not yin_token or not yang_token or (yin_token != yang_token):
                CSRF_TOKEN = secrets.token_urlsafe(32)
                if request.method != "GET":         # Reject state-changing requests from a non-CSRF compliant web client >:(
                    response = jsonify("CSRF check failed for state changing request")
                    return response, 401
                else:
                    pass

            # CSRF-Compliant web client :D
            result : Response = endpoint(*args, **kwargs)
            if isinstance(result, tuple):
                response = result[0] if isinstance(result[0], Response) else make_response(result[0])
                statusCode = result[1]
            elif isinstance(result, str):
                response = make_response(result)
                statusCode = 200
            elif not result:
                raise Exception()
            else:
                response = result
                statusCode = 200

            # Refresh CSRF token randomly hehe they'll never see it coming >:)
            if random.randint(1,10) == 1:
                CSRF_TOKEN = secrets.token_urlsafe(32)
                response.headers["X-CSRF-TOKEN"] = CSRF_TOKEN
                response.set_cookie("X-CSRF-TOKEN",
                                    value=CSRF_TOKEN,
                                    max_age=timedelta(minutes=30),
                                    httponly=True)
            return response, statusCode

        # If not web client, business as usual
        return endpoint(*args, **kwargs)
    return decorated