from jwt import decode, PyJWTError, ExpiredSignatureError
from flask import request, g
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
            auth_metadata = request.headers.get("Authorization", request.headers.get("authorization", None))
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
            if request.mimetype.split("/")[-1] != mimetype.lower():
                e = BadRequest(f"Invalid mimetype forwarded to {request.method.upper()} /{request.root_path}")
                e.__setattr__("_additional_info", f"Expected mimetype: {mimetype}, received {request.mimetype} instead")
                raise e
            return endpoint(*args, **kwargs)
        return decorated
    return inner_dec