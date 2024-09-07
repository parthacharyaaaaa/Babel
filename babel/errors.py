class Unexpected_Request_Format(Exception):
    def __init__(self, message : str = "Given request is of unexpected format") -> None:
        self.message = message
        super.__init__(self, self.message)

class Unexpected_Response_Format(Exception):
    def __init__(self, message : str = "Given response is of unexpected format") -> None:
        self.message = message
        super.__init__(self, self.message)

class Missing_Configuration_Error(Exception):
    def __init__(self, message : str = "Failure in loading configurations") -> None:
        self.message = message
        super.__init__(self, self.message)

class API_TIMEOUT_ERROR(Exception):
    def __init__(self, endpoint : str, message : str = "Timeout reached with API Endpoint: {}") -> None:
        self.message = message.format(endpoint)
        super.__init__(self, self.message)