import random
import string


def get_random_letter(length=15) -> str:
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for _ in range(length))
