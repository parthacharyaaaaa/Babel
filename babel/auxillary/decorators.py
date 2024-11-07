from jwt import decode, PyJWTError, ExpiredSignatureError
from flask import request, g
import os
from auxillary.errors import Unexpected_Request_Format
from werkzeug.exceptions import Unauthorized
from datetime import timedelta

def token_required(endpoint):
    def wrapper(*args, **kwargs):
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
    return wrapper()