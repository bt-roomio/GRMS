import re


def slugify_key(name):
    return re.sub(r"\s+", "_", name.strip().lower())
