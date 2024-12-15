class Missing_Configuration_Error(Exception):
    def __init__(self, description : str = "Failure in loading configurations") -> None:
        self.description = description
        super().__init__(self, self.description)

class API_TIMEOUT_ERROR(Exception):
    def __init__(self, endpoint : str, description : str = "Timeout reached with API Endpoint: {}") -> None:
        self.description = description.format(endpoint)
        super().__init__(self, self.description)

class DISCRETE_DB_ERROR(Exception):
    '''Only to be used to abstract away the details of a SQL error'''
    def __init__(self, description : str = "Database Service Error", *arg, **kw):
        self.description = description
        super().__init__(*arg, **kw)