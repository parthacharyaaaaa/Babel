class Unexpected_Request_Format(Exception):
    def __init__(self, message : str | None = "Given request is of unexpected format") -> None:
        self.message = message
        super.__init__(self, self.message)