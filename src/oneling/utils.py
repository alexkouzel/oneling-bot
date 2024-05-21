TIME_UNITS = [("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]

MAX_NUMBER_LEN = 3


def time_to_str(value: int) -> str:
    if value < 0:
        return "-"

    for unit_str, unit_sec in TIME_UNITS:
        if value >= unit_sec:
            return f"{value // unit_sec}{unit_str}"

    return "-"


def str_to_time_by_unit(val: str, unit) -> int:
    (unit_str, unit_sec) = unit

    # verify value min size
    if len(val) <= len(unit_str):
        return -1

    time_str = val[: -len(unit_str)]

    # verify that time is not too long
    if len(time_str) > MAX_NUMBER_LEN:
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


def str_to_time(val: str) -> int:
    if not len(val) == 0:
        for unit in TIME_UNITS:
            if val[-1] == unit[0]:
                return str_to_time_by_unit(val, unit)
    return -1
