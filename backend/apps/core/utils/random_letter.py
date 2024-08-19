import random
import string


def get_random_letter(length=15):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))
