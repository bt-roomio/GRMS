import re


def camel_to_snake(camel_case):
    # Use regular expressions to insert underscores before capital letters
    snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", camel_case).lower()
    return snake_case
