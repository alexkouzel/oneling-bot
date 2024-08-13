TIME_UNITS = [("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]


def time_to_str(value: int) -> str:
    if value < 0:
        return "-"

    for unit_str, unit_value in TIME_UNITS:
        if value >= unit_value:
            return f"{value // unit_value}{unit_str}"

    return "-"


def str_to_time_by_unit(str: str, unit: tuple[str, int]) -> int:
    (unit_str, unit_value) = unit

    # verify value min size
    if len(str) <= len(unit_str):
        return -1

    time_str = str[: -len(unit_str)]

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
        return time * unit_value

    except ValueError:
        return -1


def str_to_time(str: str) -> int:
    if not len(str) == 0:
        for unit in TIME_UNITS:
            if str[-1] == unit[0]:
                return str_to_time_by_unit(str, unit)
    return -1
