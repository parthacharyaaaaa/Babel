import json
import jwt
from datetime import timedelta
from typing import Iterable, Optional
import sqlite3
import os
import base64
import time
from datetime import datetime, timedelta

# Refresh Token
with open("static/refresh_schema.json", "r") as refreshSchema:
    REFRESH_SCHEMA : dict = json.load(refreshSchema)
    print(REFRESH_SCHEMA)  

class TokenManager:
    '''### Class for issuing and verifying access and refresh tokens assosciated with authentication and authorization
    
    #### Usage
    Instantiate TokenManager with a secret key, and use this instance to issue, verify, and revoke tokens.

    Note: It is best if only a single instance of this class is active'''

    activeRefreshTokens : int = 0 # List of non-revoked refresh tokens
    revocationList : list = []

    def __init__(self, secretKey : str, connString : str, refreshSchema : dict, accessSchema : dict, additionalChecks : dict, alg : str = "HS256", typ : str = "JWT", uClaims : Iterable = ["exp", "iat", "jit"], additioanlHeaders : dict | None = None, leeway : timedelta = timedelta(minutes=3)):
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

        self.uHeader = {"typ" : typ, "alg" : alg}
        if additioanlHeaders:
            self.uHeader.update(additioanlHeaders)

        self.uClaims = uClaims
        self.secretKey = secretKey

        self.leeway = leeway

        self.refreshHeaders, self.refreshClaims = self.processTokenSchema(self.uHeader, self.uClaims, refreshSchema)
        self.accessHeaders, self.accessClaims = self.processTokenSchema(self.uHeader, self.uClaims, accessSchema)   

    def decodeAccessToken(self, aToken : str, checkAdditionals : bool = True) -> str:
        '''Decodes an access token, raises error in case of failure'''
        decoded = jwt.decode(jwt = aToken,
                            key = self.secretKey,
                            algorithms = [self.uHeader["alg"]],
                            leeway = self.leeway)

        if (checkAdditionals and not self.additionalChecks(decoded)):
            raise PermissionError("Invalid access token")
        return decoded

    def reissueTokenPair(self, aToken : str, rToken : str) -> str:
        '''Issue a new token pair from a given refresh token
        
        params:
        
        aToken: JWT encoded access token\n
        rToken: JWT encoded refresh token'''

        if not self.verifyAccessToken(aToken): 
            raise PermissionError("Invalid access token") # Will replace permission error with a custom token error later
        
        rDecoded = jwt.decode(jwt=rToken, key=self.secretKey, algorithms=[self.uHeader["alg"]], leeway=self.leeway)
        if not self.additionalChecks(rDecoded):
            raise PermissionError("Invalid refresh token, revoking token family")
        
        accessPayload : dict = self.accessClaims
        accessPayload.update({"jit" : self.generate_unique_jit()})
        accessToken = jwt.encode(payload = self.accessClaims,
                   key = self.secretKey,
                   algorithm = self.uHeader["alg"],
                   headers = self.uHeader)

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
        payload.update(additionalClaims)

    def revokeToken(self, rToken : str, jit : Optional[str]) -> None:
        '''Revokes a refresh token, without invalidating the family'''
        try:
            if jit:
                self.cursor.execute("UPDATE tokens SET revoked = True WHERE jit = ?", (jit,))
            else:
                decodedJIT = jwt.decode(rToken, options={"verify_signature":False})["payload"]["jit"] # No need to perform computationally-intensive verification since this method is called internally by TokenManager itself after verification has been done already.
                self.cursor.execute("UPDATE tokens SET revoked = True WHERE jit = ?", (decodedJIT,))

            self.decrementActiveTokens()
            TokenManager.revocationList.append(rToken) # Dict for now, will replace with Redis store later
        except ValueError:
            print("Number of active tokens must be non-negative integer")
        except Exception as e:
            print("Error in revocation")

    def invalidateFamily(self, fID : int) -> None:
        '''Remove entire token family from revocation list and token store'''

    def verifyRefreshToken(self) -> bool:
        pass

    def additionalChecks(self) -> bool: ... # Will dynamically overwrite this in __init__, hence the "..."
    
    @staticmethod
    def decrementActiveTokens():
        if TokenManager.activeRefreshTokens == 0:
            raise ValueError("Active refresh tokens cannot be a negative number")
        TokenManager.activeRefreshTokens -= 1

    @staticmethod
    def processTokenSchema(uHeaders, uClaims, Schema : dict) -> None:
        '''Dynamically generate token claims and headers'''
        headers : dict = Schema["header"]
        for header in uHeaders:
            headers.pop(header, None)

        claims : dict = Schema["payload"]
        for claim in uClaims:
            claims.pop(claim, None)
        
        return headers, claims
    
    @staticmethod
    def generate_unique_jit():
        return base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8')