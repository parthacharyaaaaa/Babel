class Missing_Configuration_Error(Exception):
    def __init__(self, description : str = "Failure in loading configurations") -> None:
        self.description = description
        super().__init__(self, self.description)

class API_TIMEOUT_ERROR(Exception):
    def __init__(self, endpoint : str, description : str = "Timeout reached with API Endpoint: {}") -> None:
        self.description = description.format(endpoint)
        super().__init__(self, self.description)