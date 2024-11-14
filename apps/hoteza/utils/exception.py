from rest_framework.exceptions import APIException


class JsonValidationError(APIException):
    def __init__(self, detail=None, code=None):
        super().__init__(detail, code)

        for key, value in self.detail.items():
            if value.isdigit():
                self.detail[key] = int(value)
