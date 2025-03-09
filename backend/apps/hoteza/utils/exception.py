from rest_framework.exceptions import APIException


class JsonValidationError(APIException):
    status_code = 400

    def __init__(self, detail=None, code=None):
        super().__init__(detail, code)

        if isinstance(self.detail, dict):
            self.detail = {
                key: int(value) if isinstance(value, str) and value.isdigit() else value
                for key, value in self.detail.items()
            }
