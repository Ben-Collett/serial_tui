def try_parse_int(s: str) -> int | None:
    try:
        return int(s)
    except ValueError:
        return None


def clamp_int(lower, upper, val):
    if val < lower:
        return lower
    if val > upper:
        return upper
    return val
