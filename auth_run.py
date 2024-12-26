from babel_auth import auth
if __name__ == "__main__":
    auth.run(host=auth.config["HOST"], port = auth.config["PORT"], debug=True)