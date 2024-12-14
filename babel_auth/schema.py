import jwt
from datetime import timedelta
from typing import Optional
import sqlite3
from redis import Redis
import os
import base64
import time
from datetime import datetime, timedelta
from typing import TypeAlias
from functools import wraps

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

    activeRefreshTokens : int = 0 # List of non-revoked refresh tokens
    # Set up Redis

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

        self._REVOCATION_LIST_CONNECTION = Redis("localhost", port=4321, db = 1)

        # Initialize signing key (HMACSHA256)
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
                            leeway = self.leeway)

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
        refreshToken = self.issueRefreshToken(familyID=decodedRefreshToken["fid"])
        accessToken = self.issueAccessToken()
        
        return refreshToken, accessToken

    @singleThreadOnly
    def issueRefreshToken(self, sub : str, additionalClaims : Optional[dict] = None, authentication : bool = False, familyID : Optional[str] = None) -> str:
        if not authentication and familyID in TokenManager._revocationList:
            e = Exception()
            e.__setattr__("description", "Token Already Revoked")
            self.invalidateFamily(familyID)
        
        payload : dict = {"iat" : time.mktime(datetime.now().timetuple()),
                          "exp" : time.mktime((datetime.now() + self.refreshLifetime).timetuple()),
                          "nbf" : time.mktime((datetime.now() + self.refreshLifetime - self.leeway).timetuple()),

                          "sub" : sub,
                          "jti" : self.generate_unique_identifier()}
        payload.update(self.uClaims)
        if additionalClaims:
            payload.update(additionalClaims)

        if authentication:
            TokenManager.activeRefreshTokens += 1
            payload["fid"] = self.generate_unique_identifier()
        else:
            payload["fid"] = familyID

            print(payload["fid"])

        self._connectionData["cursor"].execute("INSERT INTO tokens (jit, sub, iat, exp, ipa, revoked, family_id) VALUES (?,?,?,?,?,?,?)",
                             (payload["jti"], "", payload["iat"], payload["exp"], payload.get("ipa"), False, payload["fid"] if authentication else familyID))
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

            self._connectionData["cursor"].execute("UPDATE tokens SET revoked = True WHERE jti = ?", (decoded["jti"],))
            self._connectionData["conn"].commit()

            self._REVOCATION_LIST_CONNECTION.hset(decoded['fid'], decoded["jti"], decoded['exp'])
            self._REVOCATION_LIST_CONNECTION.hexpireat(decoded['fid'], decoded['exp'], decoded["jti"])

            self.decrementActiveTokens()
        except ValueError:
            print("Number of active tokens must be non-negative integer")
        except Exception as e:
            print("Error in revocation")

    @singleThreadOnly
    def invalidateFamily(self, fID : str) -> None:
        '''Remove entire token family from revocation list and token store'''
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