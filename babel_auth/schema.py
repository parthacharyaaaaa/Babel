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

    activeRefreshTokens : int = 0

    def __init__(self, secretKey : str, refreshSchema : dict, accessSchema : dict, additionalChecks : dict, alg : str = "HS256", typ : str = "JWT", uClaims : Iterable = ["exp", "iat"], additioanlHeaders : dict | None = None, leeway : timedelta = timedelta(minutes=5)):
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

    def reissueAccessToken(self, rToken : str) -> str:
        '''Issue a new access token from a refresh token
        
        param:
        
        token: JWT encoded refresh token'''

        decoded = jwt.decode(jwt=rToken, key=self.secretKey, algorithms=[self.uHeader["alg"]], leeway=self.leeway)
        

    
    def issueRefreshToken(self) -> str:
        TokenManager.activeRefreshTokens += 1
        pass

    def verifyAccessToken(self) -> bool:
        pass

    def revokeToken(self) -> None:
        TokenManager.activeRefreshTokens -= 1
        pass

    def verifyRefreshToken(self) -> bool:
        pass


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