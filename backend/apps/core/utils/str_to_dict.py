import json


def str_to_dict(input):
    if type(input) is dict:
        return input
    try:
        if input.startswith('"') and input.endswith('"'):
            input = input[1:-1]

        input = input.replace('\\"', '"')

        return json.loads(input)
    except Exception as e:
        print(f"Second attempt failed: {e}")
