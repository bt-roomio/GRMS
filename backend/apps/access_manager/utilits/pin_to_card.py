def pin_to_card_number(pin) -> str:
    """Convert a numeric PIN into card byte notation: 123456 -> "01 02 03 04 05 06"."""
    return " ".join(f"{int(digit):02d}" for digit in str(pin))
