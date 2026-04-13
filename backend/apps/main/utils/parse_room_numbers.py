from typing import List


def parse_room_numbers(room_string: str) -> List[str]:
    """
    Преобразует строки вида:
      "100-102;104;106;" -> ["100", "101", "102", "104", "106"]
    Дополнительно:
      - Разделители: ';' или ',' (и пробелы игнорируем)
      - Диапазоны: 'A-B' (A <= B), иначе ошибка
      - Пустые части игнорируются
      - Номер без диапазона может содержать суффикс букв (например: '104ab')
    """
    if not isinstance(room_string, str):
        raise ValueError("rooms must be a string")

    raw = room_string.replace(",", ";")
    parts = [p.strip() for p in raw.strip("; ").split(";") if p.strip()]
    result: List[str] = []

    for part in parts:
        if "-" in part:
            try:
                start_str, end_str = [x.strip() for x in part.split("-", 1)]
                start, end = int(start_str), int(end_str)
            except (TypeError, ValueError):
                raise ValueError(f"Invalid range: '{part}'")
            if start > end:
                raise ValueError(f"Range start must be <= end: '{part}'")
            result.extend(str(n) for n in range(start, end + 1))
        else:
            result.append(part)

    if not result:
        raise ValueError("No room numbers parsed")

    result = list(set(result))
    return result