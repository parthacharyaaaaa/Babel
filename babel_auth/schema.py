from babel_auth import db
from sqlalchemy import Constraint
import json
import jwt
from datetime import timedelta
from typing import Iterable


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

    def __init__(self, secretKey : str, refreshSchema : dict, accessSchema : dict, additionalChecks : dict, alg : str = "HS256", typ : str = "JWT", uClaims : Iterable = ["exp", "iat"], additioanlHeaders : dict | None = None, leeway : timedelta = timedelta(minutes=3)):
        '''Initialize the token manager and set universal headers and claims, common to both access and refresh tokens
        
        params:
        
        secretKey (str): secret credential for HMAC/RSA or any other encryption algorithm in place\n
        refreshSchema (dict-like): Schema of the refresh token\n
        accessSchema (dict-like): Schema of the access token\n
        alg (str): Algorithm to use for signing, universal to all tokens\n
        typ (str): Type of token being issued, universal to all tokens\n
        uClaims (Iterable): Universal claims to include for both access and refresh tokens\n
        additonalHeaders (dict-like): Additional header information, universal to all tokens'''

        self.uHeader = {"typ" : typ, "alg" : alg}
        if additioanlHeaders:
            self.uHeader = additioanlHeaders.update(additioanlHeaders)

        self.uClaims = uClaims
        self.secretKey = secretKey

        self.leeway = leeway

        self.refreshHeaders, self.refreshClaims = self.processTokenSchema(self.uHeader, self.uClaims, refreshSchema)
        self.accessHeaders, self.accessClaims = self.processTokenSchema(self.uHeader, self.uClaims, accessSchema)

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
        
    
    def issueRefreshToken(self) -> str:
        TokenManager.activeRefreshTokens += 1
        pass

    def verifyAccessToken(self, aToken : str, checkAdditionals : bool = True) -> bool:
        try:
            decoded = jwt.decode(jwt = aToken, key = self.secretKey, algorithms = [self.uHeader["alg"]], leeway = self.leeway)
            if (checkAdditionals and not self.additionalChecks(decoded)):
                raise PermissionError("Invalid access token")
            return True
        except:
            return False

    def revokeToken(self, rToken : str) -> None:
        '''Revokes a refresh token, without invalidating the family'''
        try:
            self.decrementActiveTokens()
        except ValueError:
            print("Error in revokation")
        
        TokenManager.revocationList.append(rToken) # Dict for now, will replace with Redis store later

    def invalidateFamily(self) -> None: ...

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
        headers : dict = Schema["header"]
        for header in uHeaders:
            headers.pop(header, None)

        claims : dict = Schema["payload"]
        for claim in uClaims:
            claims.pop(claim, None)
        
        return headers, claims