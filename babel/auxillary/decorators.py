from jwt import decode, PyJWTError, ExpiredSignatureError
from flask import request, g, abort
import os
from babel.auxillary.errors import Unexpected_Request_Format
from werkzeug.exceptions import Unauthorized
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
                raise KeyError()
            auth_metadata = auth_metadata.split()[-1]
            decodedToken = decode(
                                jwt=auth_metadata,
                                key=os.environ["SECRET_KEY"],
                                algorithms=["HS256"],
                                issuer="babel-auth-service",
                                leeway=timedelta(minutes=3)
            )
            g.decodedToken = decodedToken
        except KeyError as e:
            raise Unexpected_Request_Format(f"Endpoint /{request.path[1:]} requires an authorization token to give access to resource")
        except ExpiredSignatureError:
            raise  Unauthorized("JWT token expired, begin refresh issuance")
        except PyJWTError:
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
            if request.mimetype.split()[-1] != mimetype.lower():
                raise Unexpected_Request_Format("Invalid mimetype forwarded to the endpoint")
            return endpoint(*args, **kwargs)
        return decorated
    return inner_dec