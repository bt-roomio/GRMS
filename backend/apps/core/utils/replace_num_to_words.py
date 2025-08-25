import re

from num2words import num2words


def replace_numbers_with_words(text: str, lang: str = "en", max_digits: int = 10) -> str:
    pattern = re.compile(r"\b\d+\b")

    def repl(m: re.Match):
        s = m.group(0)
        if len(s) > max_digits:
            return s
        try:
            return num2words(int(s), lang=lang)
        except Exception:
            return s

    return pattern.sub(repl, text)
