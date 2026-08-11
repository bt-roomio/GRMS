import secrets


def get_random_letter(length=15) -> str:
    return secrets.token_hex(length)
