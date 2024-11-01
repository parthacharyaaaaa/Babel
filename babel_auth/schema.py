import json
import jwt
from datetime import timedelta
from typing import Iterable, Optional
import sqlite3
import os
import base64
import time
from datetime import datetime, timedelta

class TokenManager:
    '''### Class for issuing and verifying access and refresh tokens assosciated with authentication and authorization
    
    #### Usage
    Instantiate TokenManager with a secret key, and use this instance to issue, verify, and revoke tokens.

    Note: It is best if only a single instance of this class is active'''

    activeRefreshTokens : int = 0 # List of non-revoked refresh tokens
    revocationList : list = []

    def __init__(self, secretKey : str,
                 connString : str,
                 refreshSchema : dict,
                 accessSchema : dict, 
                 alg : str = "HS256",
                 typ : str = "JWT",
                 uClaims : dict = {"iss" : "babel-auth-service"},
                 additioanlHeaders : dict | None = None,
                 leeway : timedelta = timedelta(minutes=3)):
        '''Initialize the token manager and set universal headers and claims, common to both access and refresh tokens
        
        params:
        
        secretKey (str): secret credential for HMAC/RSA or any other encryption algorithm in place\n
        connString (str): Database URI string for establishing connection to db\n
        refreshSchema (dict-like): Schema of the refresh token\n
        accessSchema (dict-like): Schema of the access token\n
        alg (str): Algorithm to use for signing, universal to all tokens\n
        typ (str): Type of token being issued, universal to all tokens\n
        uClaims (Iterable): Universal claims to include for both access and refresh tokens\n
        additonalHeaders (dict-like): Additional header information, universal to all tokens'''

        self.conn = sqlite3.connect(connString, uri=True)
        self.cursor = sqlite3.Cursor(self.conn)

        # Initialize signing key (HMAC SHA 256)
        self.secretKey = secretKey

        # Initialize universal headers, common to all tokens issued in any context
        uHeader = {"typ" : typ, "alg" : alg}
        if additioanlHeaders:
            uHeader.update(additioanlHeaders)

        # Initialize specific headers, if any, for refresh and access tokens respectively
        self.refreshHeaders = uHeader.update(refreshSchema["header"]) or {}
        self.accessHeaders = uHeader.update(accessSchema["header"])  or {}

        # Initialize universal claims, common to all tokens issued in any context. 
        # These should at the very least contain registered claims like "exp"
        self.uClaims = uClaims

        # Set leeway for time-related claims
        self.leeway = leeway

    def decodeToken(self, token : str, checkAdditionals : bool = True, tType : str = "access") -> str:
        '''Decodes an access token, raises error in case of failure'''
        decoded = jwt.decode(jwt = token,
                            key = self.secretKey,
                            algorithms = [self.accessHeaders["alg"]],
                            leeway = self.leeway)

        # if (checkAdditionals and not self.additionalChecks(decoded)):
        #     raise PermissionError("Invalid access token")
        return decoded

    def reissueTokenPair(self, rToken : str) -> str:
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
        refreshToken = self.issueRefreshToken()
        accessToken = self.issueAccessToken()
        
        return refreshToken, accessToken

    def issueRefreshToken(self, authentication : bool = False) -> str:
        if authentication:
            TokenManager.activeRefreshTokens += 1
        pass

    def issueAccessToken(self, additionalClaims : dict) -> str:
        # Handling registered claim names:
        payload : dict = {"iat" : time.mktime(datetime.now().timetuple()),
                          "exp" : time.mktime((datetime.now() + timedelta(minutes=15)).timetuple()),
                          "nbf" : time.mktime((datetime.now() - timedelta(minutes=13)).timetuple()),
                          
                          "jit" : self.generate_unique_jit()}
        payload.update(self.uClaims)

    def revokeToken(self, rToken : str) -> None:
        '''Revokes a refresh token, without invalidating the family'''
        try:
            decodedJIT = jwt.decode(rToken, options={"verify_signature":False})["payload"]["jit"] # No need to perform computationally-intensive verification since this method is called internally by TokenManager itself after verification has been done already.
            self.cursor.execute("UPDATE tokens SET revoked = True WHERE jit = ?", (decodedJIT,))

            TokenManager.revocationList.append({"jit" : decodedJIT["jit"], "fid" : decodedJIT["fid"]}) # Dict for now, will replace with Redis store later
            self.decrementActiveTokens()
        except ValueError:
            print("Number of active tokens must be non-negative integer")
        except Exception as e:
            print("Error in revocation")

    def invalidateFamily(self, fID : int) -> None:
        '''Remove entire token family from revocation list and token store'''
        ...

    @staticmethod
    def decrementActiveTokens():
        if TokenManager.activeRefreshTokens == 0:
            raise ValueError("Active refresh tokens cannot be a negative number")
        TokenManager.activeRefreshTokens -= 1
    
    @staticmethod
    def generate_unique_jit():
        return base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8')