from typing import List


def parse_room_numbers(room_string: str) -> List[int]:
    """
    Преобразует строки вида:
      "100-102;104;106;" -> [100, 101, 102, 104, 106]
    Дополнительно:
      - Разделители: ';' или ',' (и пробелы игнорируем)
      - Диапазоны: 'A-B' (A <= B), иначе ошибка
      - Пустые части игнорируются
    """
    if not isinstance(room_string, str):
        raise ValueError("rooms must be a string")

    raw = room_string.replace(",", ";")
    parts = [p.strip() for p in raw.strip("; ").split(";") if p.strip()]
    result: List[int] = []

    for part in parts:
        if "-" in part:
            try:
                start_str, end_str = [x.strip() for x in part.split("-", 1)]
                start, end = int(start_str), int(end_str)
            except (TypeError, ValueError):
                raise ValueError(f"Invalid range: '{part}'")
            if start > end:
                raise ValueError(f"Range start must be <= end: '{part}'")
            result.extend(range(start, end + 1))
        else:
            try:
                result.append(int(part))
            except ValueError:
                raise ValueError(f"Invalid number: '{part}'")

    if not result:
        raise ValueError("No room numbers parsed")

    result = list(sorted(set(result)))
    return result
