class Missing_Configuration_Error(Exception):
    def __init__(self, message : str = "Failure in loading configurations") -> None:
        self.message = message
        super().__init__(self, self.message)

class API_TIMEOUT_ERROR(Exception):
    def __init__(self, endpoint : str, message : str = "Timeout reached with API Endpoint: {}") -> None:
        self.message = message.format(endpoint)
        super().__init__(self, self.message)