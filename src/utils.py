TIME_UNITS = [("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]


def time_to_text(value: int) -> str:
    if value < 0:
        return "-"

    for unit_str, unit_sec in TIME_UNITS:
        if value >= unit_sec:
            return f"{value // unit_sec}{unit_str}"

    return "-"


def text_to_time_by_unit(text: str, unit) -> int:
    (unit_str, unit_sec) = unit

    # verify value min size
    if len(text) <= len(unit_str):
        return -1

    time_str = text[: -len(unit_str)]

    # verify that time is not too long (>3 symbols)
    if len(time_str) > 3:
        return -1

    try:
        # try to convert time to an integer
        time = int(time_str)

        # check that time is at least 1
        if time < 1:
            return -1

        # convert time to seconds and return
        return time * unit_sec

    except ValueError:
        return -1


def text_to_time(text: str) -> int:
    if not len(text) == 0:
        for unit in TIME_UNITS:
            if text[-1] == unit[0]:
                return text_to_time_by_unit(text, unit)
    return -1
