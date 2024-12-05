from shuttle.utils.camel_to_snake import to_camelcase_data, to_snake_case_data


class CamelCaseMixin:
    def to_representation(self, *args, **kwargs):
        return to_camelcase_data(super().to_representation(*args, **kwargs))

    def to_internal_value(self, data):
        return super().to_internal_value(to_snake_case_data(data))
