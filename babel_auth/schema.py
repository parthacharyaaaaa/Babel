import jwt
from datetime import timedelta
from typing import Optional
import sqlite3
import os
import base64
import time
from datetime import datetime, timedelta
from typing import TypeAlias

# Aliases
tokenPair : TypeAlias = tuple[str, str]

class TokenManager:
    '''### Class for issuing and verifying access and refresh tokens assosciated with authentication and authorization
    
    #### Usage
    Instantiate TokenManager with a secret key, and use this instance to issue, verify, and revoke tokens.

    Note: It is best if only a single instance of this class is active'''

    activeRefreshTokens : int = 0 # List of non-revoked refresh tokens
    _revocationList : list = []

    def __init__(self, secretKey : str,
                 _connString : str,
                 refreshSchema : dict,
                 accessSchema : dict, 
                 alg : str = "HS256",
                 typ : str = "JWT",
                 uClaims : dict = {"iss" : "babel-auth-service"},
                 uHeaders : dict | None = None,
                 leeway : timedelta = timedelta(minutes=3)):
        '''Initialize the token manager and set universal headers and claims, common to both access and refresh tokens
        
        params:
        
        secretKey (str): secret credential for HMAC/RSA or any other encryption algorithm in place\n
        _connString (str): Database URI string for establishing _connection to db\n
        refreshSchema (dict-like): Schema of the refresh token\n
        accessSchema (dict-like): Schema of the access token\n
        alg (str): Algorithm to use for signing, universal to all tokens\n
        typ (str): Type of token being issued, universal to all tokens\n
        uClaims (dict-like): Universal claims to include for both access and refresh tokens\n
        additonalHeaders (dict-like): Additional header information, universal to all tokens'''

        self._conn = sqlite3._connect(_connString, uri=True)
        self._cursor = sqlite3._cursor(self._conn)

        # Initialize signing key (HMACSHA256)
        self.secretKey = secretKey

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
                            key = self.secretKey,
                            algorithms = [self.accessHeaders["alg"] if tType == "access" else self.refreshHeaders["alg"]],
                            leeway = self.leeway)

    def reissueTokenPair(self, rToken : str) -> tokenPair:
        '''Issue a new token pair from a given refresh token
        
        params:
        
        aToken: JWT encoded access token\n
        rToken: JWT encoded refresh token'''
        try:
            decodedRefreshToken = self.decodeToken(rToken, tType = "refresh")
            self.revokeToken(decodedRefreshToken["jit"])
        except:
            raise PermissionError("Invalid token") # Will replace permission error with a custom token error later
        
        # issue tokens here
        refreshToken = self.issueRefreshToken(familyID=decodedRefreshToken["fid"])
        accessToken = self.issueAccessToken()
        
        return refreshToken, accessToken

    def issueRefreshToken(self, additionalClaims : Optional[dict] = None, authentication : bool = False, familyID : Optional[str] = None) -> str:
        payload : dict = {"iat" : time.mktime(datetime.now().timetuple()),
                          "exp" : time.mktime((datetime.now() + self.refreshLifetime).timetuple()),
                          "nbf" : time.mktime((datetime.now() + self.refreshLifetime - self.leeway).timetuple()),
                          
                          "jit" : self.generate_unique_identifier()}
        payload.update(self.uClaims)
        payload.update(additionalClaims)

        if authentication:
            TokenManager.activeRefreshTokens += 1
            payload.update({"fid" : self.generate_unique_identifier()})
        else:
            payload.update({"fid" : familyID})
        
        self._cursor.execute("INSERT INTO tokens (jit, sub, iat, exp, ipa, revoked, family_id) VALUES (?,?,?,?,?,?,?)", (payload["jit"], None, payload["iat"], payload["exp"], payload.get("ipa"), False, payload["fid"] if authentication else familyID))
        self._conn.commit()
        return jwt.encode(payload=payload,
                          key=self.secretKey,
                          algorithm=self.refreshHeaders["alg"],
                          headers=self.refreshHeaders)

    def issueAccessToken(self, additionalClaims : dict) -> str:
        payload : dict = {"iat" : time.mktime(datetime.now().timetuple()),
                          "exp" : time.mktime((datetime.now() + self.accessLifetime).timetuple()),
                          "nbf" : time.mktime((datetime.now() + self.accessLifetime - self.leeway).timetuple()),
                          
                          "jit" : self.generate_unique_identifier()}
        payload.update(self.uClaims)
        payload.update(additionalClaims)
        return jwt.encode(payload=payload,
                          key=self.secretKey,
                          algorithm=self.accessHeaders["alg"],
                          headers=self.accessHeaders)

    def revokeToken(self, rToken : str) -> None:
        '''Revokes a refresh token, without invalidating the family'''
        try:
            decodedJIT = jwt.decode(rToken, options={"verify_signature":False})["payload"]["jit"] # No need to perform computationally-intensive verification since this method is called internally by TokenManager itself after verification has been done already.
            self._cursor.execute("UPDATE tokens SET revoked = True WHERE jit = ?", (decodedJIT,))
            self._conn.commit()

            TokenManager._revocationList.append({"jit" : decodedJIT["jit"], "fid" : decodedJIT["fid"]}) # Dict for now, will replace with Redis store later
            self.decrementActiveTokens()
        except ValueError:
            print("Number of active tokens must be non-negative integer")
        except Exception as e:
            print("Error in revocation")

    def invalidateFamily(self, fID : str) -> None:
        '''Remove entire token family from revocation list and token store'''
        self._cursor.execute("DELETE FROM tokens WHERE family_id = ?", (fID,))
        self._conn.commit()

    @staticmethod
    def decrementActiveTokens():
        if TokenManager.activeRefreshTokens == 0:
            raise ValueError("Active refresh tokens cannot be a negative number")
        TokenManager.activeRefreshTokens -= 1
    
    @staticmethod
    def generate_unique_identifier():
        return base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8')