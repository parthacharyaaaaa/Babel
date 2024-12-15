import jwt
from datetime import timedelta
from typing import Optional
import sqlite3
from babel_auth.auxillary.errors import Missing_Configuration_Error
from auxillary_packages.RedisManager import Cache_Manager
import os
import base64
import time
from datetime import datetime, timedelta
from typing import TypeAlias
from functools import wraps
from jwt.exceptions import PyJWTError, DecodeError, ExpiredSignatureError, InvalidIssuedAtError, InvalidIssuerError

# Aliases
tokenPair : TypeAlias = tuple[str, str]

# Helper
def singleThreadOnly(func):
    @wraps(func)
    def decorated(self, *args, **kwargs):
        self._connectionData["conn"]= sqlite3.connect(self._connString, uri=True)
        self._connectionData["cursor"] = sqlite3.Cursor(self._connectionData["conn"])
        try:
            op = func(self, *args, **kwargs)
        finally:
            self._connectionData["conn"].close()
            self._connectionData.clear()
        
        return op
    return decorated

class TokenManager:
    '''### Class for issuing and verifying access and refresh tokens assosciated with authentication and authorization
    
    #### Usage
    Instantiate TokenManager with a secret key, and use this instance to issue, verify, and revoke tokens.

    Note: It is best if only a single instance of this class is active'''

    activeRefreshTokens : int = 0

    def __init__(self, signingKey : str,
                 connString : str,
                 refreshSchema : dict,
                 accessSchema : dict, 
                 alg : str = "HS256",
                 typ : str = "JWT",
                 uClaims : dict = {"iss" : "babel-auth-service"},
                 uHeaders : dict | None = None,
                 leeway : timedelta = timedelta(minutes=3)):
        '''Initialize the token manager and set universal headers and claims, common to both access and refresh tokens
        
        params:
        
        signingKey (str): secret credential for HMAC/RSA or any other encryption algorithm in place\n
        _connString (str): Database URI string for establishing _connection to db\n
        refreshSchema (dict-like): Schema of the refresh token\n
        accessSchema (dict-like): Schema of the access token\n
        alg (str): Algorithm to use for signing, universal to all tokens\n
        typ (str): Type of token being issued, universal to all tokens\n
        uClaims (dict-like): Universal claims to include for both access and refresh tokens\n
        additonalHeaders (dict-like): Additional header information, universal to all tokens'''

        self._connString = connString
        self._connectionData = dict()
        try:
            self._TokenStore = Cache_Manager(os.environ["REDIS_HOST"],
                             os.environ["REDIS_PORT"],
                             os.environ["REDIS_DB"])
        except:
            raise Missing_Configuration_Error()

        # Initialize signing key
        self.signingKey = signingKey

        # Initialize universal headers, common to all tokens issued in any context
        uHeader = {"typ" : typ, "alg" : alg}
        if uHeaders:
            uHeader.update(uHeaders)

        # Initialize specific headers, if any, for refresh and access tokens respectively
        self.refreshHeaders = dict(uHeader, **refreshSchema["header"])
        self.accessHeaders = dict(uHeader, **accessSchema["header"])

        # Initialize universal claims, common to all tokens issued in any context. 
        # These should at the very least contain registered claims like "exp"
        self.uClaims = uClaims

        self.refreshLifetime = timedelta(minutes=refreshSchema["metadata"]["lifetime"])
        self.accessLifetime = timedelta(minutes=accessSchema["metadata"]["lifetime"])

        # Set leeway for time-related claims
        self.leeway = leeway

    def decodeToken(self, token : str, checkAdditionals : bool = True, tType : str = "access") -> str:
        '''Decodes an access token, raises error in case of failure'''
        return jwt.decode(jwt = token,
                        key = self.signingKey,
                        algorithms = [self.accessHeaders["alg"] if tType == "access" else self.refreshHeaders["alg"]],
                        leeway = self.leeway,
                        issuer="babel-auth-service")

    def reissueTokenPair(self, rToken : str) -> tokenPair:
        '''Issue a new token pair from a given refresh token
        
        params:
        
        aToken: JWT encoded access token\n
        rToken: JWT encoded refresh token'''
        try:
            decodedRefreshToken = self.decodeToken(rToken, tType = "refresh")
            self.revokeToken(decodedRefreshToken["jti"])
        except:
            raise PermissionError("Invalid token") # Will replace permission error with a custom token error later
        
        # issue tokens here
        refreshToken = self.issueRefreshToken(decodedRefreshToken["sub"], firstTime=False, jti=decodedRefreshToken["jti"], familyID=decodedRefreshToken["fid"], exp=decodedRefreshToken["exp"])
        accessToken = self.issueAccessToken()
        
        return refreshToken, accessToken

    @singleThreadOnly
    def issueRefreshToken(self, sub : str, additionalClaims : Optional[dict] = None, firstTime : bool = False, jti : Optional[str] = None, familyID : Optional[str] = None, exp : Optional[int] = None) -> str:
        '''Issue a refresh token
        
        params:
        
        sub: subject of the JWT
        
        additionalClaims: Additional claims to attach to the JWT body
        
        firstTime: Whether issuance is assosciated with a new authorization flow or not

        jti: JTI claim of the current refresh token

        familyID: FID claim of the current refresh token
        '''
        # Check for replay attack
        if not firstTime:
            key = self._TokenStore.lindex(f"FID:{familyID}", 0)
            if not key:
                self.invalidateFamily(familyID)
            key_metadata = key.split(":")
            if key_metadata[0] != jti or key_metadata[1] != exp:
                self.invalidateFamily(familyID)

        elif self._TokenStore.get(f"FID{familyID}"):
            self.invalidateFamily(familyID)

        payload : dict = {"iat" : time.mktime(datetime.now().timetuple()),
                          "exp" : time.mktime((datetime.now() + self.refreshLifetime).timetuple()),
                          "nbf" : time.mktime((datetime.now() + self.refreshLifetime - self.leeway).timetuple()),

                          "sub" : sub,
                          "jti" : self.generate_unique_identifier()}
        payload.update(self.uClaims)
        if additionalClaims:
            payload.update(additionalClaims)

        if firstTime:
            TokenManager.activeRefreshTokens += 1
            payload["fid"] = self.generate_unique_identifier()
        else:
            payload["fid"] = familyID
            self.revokeTokenWithIDs(payload['jti'], familyID)

        self._TokenStore.lpush(payload['fid'], f"{payload['jti']}:{payload['exp']}")

        self._connectionData["cursor"].execute("INSERT INTO tokens (jti, sub, iat, exp, ipa, revoked, family_id) VALUES (?,?,?,?,?,?,?)",
                             (payload["jti"], "", payload["iat"], payload["exp"], payload.get("ipa"), False, payload["fid"] if firstTime else familyID))
        self._connectionData["conn"].commit()
        return jwt.encode(payload=payload,
                          key=self.signingKey,
                          algorithm=self.refreshHeaders["alg"],
                          headers=self.refreshHeaders)

    def issueAccessToken(self, sub : str, additionalClaims : Optional[dict] = None) -> str:
        payload : dict = {"iat" : time.mktime(datetime.now().timetuple()),
                          "exp" : time.mktime((datetime.now() + self.accessLifetime).timetuple()),
                          "iss" : "babel-auth-service",
                          
                          "sub" : sub,
                          "jti" : self.generate_unique_identifier()}
        payload.update(self.uClaims)
        if additionalClaims:
            payload.update(additionalClaims)
        return jwt.encode(payload=payload,
                          key=self.signingKey,
                          algorithm=self.accessHeaders["alg"],
                          headers=self.accessHeaders)

    @singleThreadOnly
    def revokeToken(self, rToken : str, verify : bool = False) -> None:
        '''Revokes a refresh token, without invalidating the family'''
        try:
            decoded = jwt.decode(rToken, options={"verify_signature":verify})["payload"]

            self._TokenStore.rpop(f"FID:{decoded['fid']}")

            self._connectionData["cursor"].execute("UPDATE tokens SET revoked = True WHERE jti = ?", (decoded["jti"],))
            self._connectionData["conn"].commit()

            self.decrementActiveTokens()
        except ValueError:
            print("Number of active tokens must be non-negative integer")
        except Exception as e:
            print("Error in revocation")

    @singleThreadOnly
    def revokeTokenWithIDs(self, jti : str, fID : str) -> None:
        '''Revokes a refresh token using JTI and FID claims, without invalidating the family'''
        try:
            self._TokenStore.rpop(fID)

            self._connectionData["cursor"].execute("UPDATE tokens SET revoked = True WHERE jti = ?", (jti,))
            self._connectionData["conn"].commit()

            self.decrementActiveTokens()
        except ValueError:
            print("Number of active tokens must be non-negative integer")
        except Exception as e:
            print("Error in revocation")

    @singleThreadOnly
    def invalidateFamily(self, fID : str) -> None:
        '''Remove entire token family from revocation list and token store'''
        self._TokenStore.delete(f"FID:{fID}")

        self._connectionData["cursor"].execute("DELETE FROM tokens WHERE family_id = ?", (fID,))
        self._connectionData["conn"].commit()

    @staticmethod
    def decrementActiveTokens():
        if TokenManager.activeRefreshTokens == 0:
            raise ValueError("Active refresh tokens cannot be a negative number")
        TokenManager.activeRefreshTokens -= 1
    
    @staticmethod
    def generate_unique_identifier():
        return base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8')