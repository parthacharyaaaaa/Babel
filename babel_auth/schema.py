import jwt
from typing import Optional, Literal
from auxillary_packages.errors import Missing_Configuration_Error, TOKEN_STORE_INTEGRITY_ERROR
from auxillary_packages.RedisManager import REDIS_MANAGER
from werkzeug.exceptions import InternalServerError
import os
import uuid
import time
from typing import TypeAlias
import jwt.exceptions as JWTexc

# Aliases
tokenPair : TypeAlias = tuple[str, str]

class TokenManager:
    '''### Class for issuing and verifying access and refresh tokens assosciated with authentication and authorization
    
    #### Usage
    Instantiate TokenManager with a secret key, and use this instance to issue, verify, and revoke tokens.

    Note: It is best if only a single instance of this class is active'''

    activeRefreshTokens : int = 0

    def __init__(self, signingKey : str,
                 refreshSchema : dict,
                 accessSchema : dict, 
                 alg : str = "HS256",
                 typ : str = "JWT",
                 uClaims : dict = {"iss" : "babel-auth-service"},
                 uHeaders : dict | None = None,
                 leeway : int = 180,
                 max_tokens_per_fid : int = 3):
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

        try:
            self._TokenStore = REDIS_MANAGER(os.environ["REDIS_HOST"],
                             os.environ["REDIS_PORT"],
                             os.environ["REDIS_DB"])
            self.max_llen = max_tokens_per_fid
        except Exception as e:
            raise Missing_Configuration_Error("Mandatory configurations missing for _TokenStore") from e

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

        self.refreshLifetime = refreshSchema["metadata"]["lifetime"]
        self.accessLifetime = accessSchema["metadata"]["lifetime"]

        # Set leeway for time-related claims
        self.leeway = leeway

    def decodeToken(self, token : str, checkAdditionals : bool = True, tType : Literal["access", "refresh"] = "access", **kwargs) -> str:
        '''Decodes token, raises error in case of failure'''
        try:
            return jwt.decode(jwt = token,
                            key = self.signingKey,
                            algorithms = [self.accessHeaders["alg"] if tType == "access" else self.refreshHeaders["alg"]],
                            leeway = self.leeway,
                            issuer="babel-auth-service",
                            options=kwargs.get('options'))
        except (JWTexc.ImmatureSignatureError, JWTexc.InvalidIssuedAtError, JWTexc.InvalidIssuerError) as e:
            if tType == "refresh":
                self.invalidateFamily(jwt.decode(token, options={"verify_signature":False})["fid"])
            raise TOKEN_STORE_INTEGRITY_ERROR("PP")

    def reissueTokenPair(self, rToken : str) -> tokenPair:
        '''Issue a new token pair from a given refresh token
        
        params:
        
        aToken: JWT encoded access token\n
        rToken: JWT encoded refresh token'''
        self.incrementActiveTokens()
        decodedRefreshToken = self.decodeToken(rToken, tType = "refresh")
        self.revokeTokenWithIDs(decodedRefreshToken["jti"], decodedRefreshToken['fid'])

        # issue tokens here
        refreshToken = self.issueRefreshToken(decodedRefreshToken["sub"],
                                              firstTime=False,
                                              jti=decodedRefreshToken["jti"],
                                              familyID=decodedRefreshToken["fid"],
                                              exp=decodedRefreshToken["exp"])
        accessToken = self.issueAccessToken(decodedRefreshToken['sub'],
                                            additionalClaims={"fid" : decodedRefreshToken["fid"]})
        
        return refreshToken, accessToken

    def issueRefreshToken(self, sub : str,
                          additionalClaims : Optional[dict] = None,
                          firstTime : bool = False,
                          jti : Optional[str] = None,
                          familyID : Optional[str] = None,
                          exp : Optional[int] = None) -> str:
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
                raise TOKEN_STORE_INTEGRITY_ERROR(f"Token family {familyID} is invalid or empty")
            key_metadata = key.split(":")
            if key_metadata[0] != jti or float(key_metadata[1]) != exp:
                self.invalidateFamily(familyID)
                raise TOKEN_STORE_INTEGRITY_ERROR(f"Replay attack detected or token metadata mismatch for family {familyID}")

        elif self._TokenStore.get(f"FID{familyID}"):
            self.invalidateFamily(familyID)
            raise TOKEN_STORE_INTEGRITY_ERROR(f"Token family {familyID} already exists, cannot issue a new token with the same family")

        payload : dict = {"iat" : time.time(),
                          "exp" : time.time() + self.refreshLifetime,
                          "nbf" : time.time() + self.accessLifetime - self.leeway,

                          "sub" : sub,
                          "jti" : self.generate_unique_identifier()}
        payload.update(self.uClaims)
        if additionalClaims:
            payload.update(additionalClaims)

        if firstTime:
            payload["fid"] = self.generate_unique_identifier()
        else:
            payload["fid"] = familyID

        self._TokenStore.lpush(f"FID:{payload['fid']}", f"{payload['jti']}:{payload['exp']}")
        self._TokenStore.expireat(f"FID:{payload['fid']}", int(payload["exp"]))

        return jwt.encode(payload=payload,
                          key=self.signingKey,
                          algorithm=self.refreshHeaders["alg"],
                          headers=self.refreshHeaders)

    def issueAccessToken(self, sub : str, 
                         additionalClaims : Optional[dict] = None) -> str:
        payload : dict = {"iat" : time.time(),
                          "exp" : time.time() + self.accessLifetime,
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

    def revokeTokenWithIDs(self, jti : str, fID : str) -> None:
        '''Revokes a refresh token using JTI and FID claims, without invalidating the family'''
        try:
            llen = self._TokenStore.llen(f"FID:{fID}")

            if llen == 0:
                return "Key does not exist"
            
            if llen >= self.max_llen:
                self._TokenStore.rpop(f"FID:{fID}", max(1, llen-self.max_llen))

            self.decrementActiveTokens()
        except ValueError as e:
            print("Number of active tokens must be non-negative integer")
        except Exception as e:
            raise InternalServerError("Failed to perform operation on token store")

    def invalidateFamily(self, fID : str) -> None:
        '''Remove entire token family from revocation list and token store'''
        try:
            if self._TokenStore.get(f"FID:{fID}"):
                self._TokenStore.delete(f"FID:{fID}")
                self.decrementActiveTokens()
            else:
                print("No Family Found")
        except Exception as e:
            raise InternalServerError("Failed to perform operation on token store")

    @staticmethod
    def decrementActiveTokens():
        if TokenManager.activeRefreshTokens == 0:
            raise ValueError("Active refresh tokens cannot be a negative number")
        TokenManager.activeRefreshTokens -= 1

    @staticmethod
    def incrementActiveTokens():
        TokenManager.activeRefreshTokens += 1
    
    @staticmethod
    def generate_unique_identifier():
        return uuid.uuid4().hex