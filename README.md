
# Babel + Auth
This project consists of 2 separate services.
- One being a resource server which is effectively a simple API wrapper for translating text and transcripting speech, with basic CRUD functionality to look like a legitimate service.
- The other being an auth server, responsible for issuance, rotation, and revocation of access and refresh JWTs. This service also handles issuance of CSRF tokens.

## Installation Guide
#### Required softwares:
- Python 3.10 or higher, along with a somewhat up-to-date package manager
- Redis: 7.4.1 or higher
- SQLite 3.45.1 or higher

#### Getting started
1) Clone the repository:
```bash 
$ git clone git@github.com:parthacharyaaaaa/Babel.git
```
or 
```bash
$ git clone https://github.com/parthacharyaaaaa/Babel.git
```

2) Install dependencies:
```bash
$ pip install -r requirements.txt
```

3) Set up environment variables: Babel and Babel_auth depend on many variables that need to be declared explicitly in dedicated `.env` files. For convenience, `.env.example` files have been provided.

4) Redis setup: Each of the 2 Flask servers depend on a Redis layer for either caching (Resource Server) or token management (Auth Server). For this, you will need to start 2 Redis servers.

The `REDIS_MANAGER` class in `auxillary_packages/RedisManager.py` is solely responsible for all Redis-related operations. 

Based on the Redis configurations you have added to the 2 .env files, perform the following command:
```bash
$ sudo redis-server --port PORT
```
* Replace PORT with the respective ports.
I also suggest having AOF enabled for the token store, which can be done by creating a `redis.conf` file and setting `AOF`. The new command would then look like:
```bash
$ sudo redis-server /path/to/AOF_enabled.conf --port PORT
```

5) Running the services
Now that Redis is up and running. Navigate to the CWD (i.e. ./babel/) and run the following commands:
```bash
$ python ./run.py
```
Resource Server

```basg
$ python ./auth_run.py
```
Auth Server
## Usage
#### Note: For CSRF compliance, the services rely on the HTTP header `X-CLIENT-TYPE` to determine whether an incoming HTTP request is from a web client or not. If you are not using a web browser, make sure to attach an appropriate `X-CLIENT-TYPE` header to all requests (can be set to `test`) to mitigate the unneeded CSRF check.

First, create an account by sending a `POST` request to `auth_server/register` (replace auth-server with the actual IP address) with the following details in the `JSON` body:
```JSON
    "username" : "username",
    "email" : "email@email.com",
    "password" : "password123",
    "cpassword" : "password123"
```

Change the details as needed, unless you are fond of password123 as an actual password.

The returned response should be an HTTP `201 OK`, indicating that an account has been created. 
Equally importantly, you will receive an access token and a refresh token in the form of cookies. These will be used as Bearer tokens to authorize any subsequent requests. 

On access token expiry, `silent_reauth.js` would automatically handle token reiussance for web clients. Otherwise, periodic `GET` requests to `auth_server/reissue` are needed for reiussance. The response for `auth_server/reissue` is the same as `auth_server/register`

### A few other endpoints

- `POST auth_server/login` expects `identity` and `password` in the request's JSON body. `identity` can be either username or email address, the distinction is done server-side.

- `GET auth_server/purge-family` is used for logouts or any detected replay attacks (Although replay attacks are inherently detected by `TokenManager`). 

- `POST resource_server/translate-text` expects the following `JSON` body:
```JSON
    "text" : "Python boasts a lot of features like subpar performance, lack of static typing, and forced indentation",
    "dest" : "fr",
    "src" : "en"
```
"src" can be excluded, server-side logic accounts for auto-detection of source language.

- `POST resource_server/transcript-speech` expects an `audio-file` in the `multipart/form-data` request. The file should not exceed 25MB. The server transcribes the audio to text and returns the transcription with confidence and processing time. If the file is too large, a `400 Bad Request` is returned.

- `GET resource_server/fetch-history?page=x&sort=y&filter=z` can be used to fetch history (I know, you would have never guessed) based on 3 query params. The user against which to query the DB is decided through the `sub` claim in the access JWT.

- `DELETE resource_server/delete-account` requires the correct account password and a valid refresh JWT to delete the account.

## Features
- RESTful design
- Strict, configurable CSP headers after every request
- CORS policy
- CSRF-Protection, enforced via double submissions of identical tokens, stored as `httponly` cookie and in `localStorage`
- IP checks and API key checks for private endpoints
- Comprehensive JWT policy, including efficient replay attack detection, prompt revocation for both individual tokens and entire token families, reissuance schemes, and rotation.
- Secure storage of bearer tokens as `httponly` cookies, with configured paths for refresh tokens as well.
- Redis-based token storage, ensuring blazingly fast speed for token issuance and checks.
- Comprehensive database schema, with proper migrations and integrity checks.
- Redis caching for resource server, greatly cutting down latency.
- Robust decorators for common operations like enforcing mimetypes, checking tokens, protecting against CSRF, and private communications between Babel servers.
- Complete account management functionality
- Recording of user history, option to sort/filter through results.
- Proper error handlers for all possible exceptions (Normal, HTTPexceptions, and RedisExceptions).

## Acknowledgements
This project, even if built solely by me, is far from an individual effort. I would like to thank:
- Redis: For keeping things fast and efficient, one key at a time. Watching latency drop by as much as 80% for some endpoints was pure bliss.
- OAuth2.0: For their comprehensive resources on JWT-based authentication and authorization, as well as the OAuth flow.
- OWasp: For their documentation on best practices for web security.
- Py-JWT: For simplifying JWT handling in Python.
- Stack Overflow: The sub-10 upvote answers are what hold this community together.
- Flask Community: For making web development feel like second nature.

And the creators, maintainers, and community revolving around all of the languages, tools, libraries, and any other software I have used.
