<<<<<<< HEAD
#!/usr/bin/env python3
r"""
A tool to normalise times to the nearest multiple (eg. 60minutes), so a distribution can be viewed more readily

eg.
    $ sqlite3 posts.sqlite3 'select username,date from posts where ticker is "AFC"' | sed -E 's/\ ?\|.*\ / /;s/://g;s/00$//' > usertimes.out
    $ ./normalise.py usertimes.out 60 | grep -i anneowl | distribution --color --height=50 | sort -n +1
             Key|Ct (Pct)   Histogram
    AnneOwl 0000| 3 (0.87%) ------
    AnneOwl 0100| 1 (0.29%) --
    AnneOwl 0300| 1 (0.29%) --
    AnneOwl 0400| 1 (0.29%) --
    AnneOwl 0600| 1 (0.29%) --
    AnneOwl 0700| 4 (1.16%) -------
    AnneOwl 0800|20 (5.81%) -----------------------------------
    AnneOwl 0900|30 (8.72%) ----------------------------------------------------
    AnneOwl 1000|27 (7.85%) -----------------------------------------------
    AnneOwl 1100|26 (7.56%) ---------------------------------------------
    AnneOwl 1200|18 (5.23%) -------------------------------
    AnneOwl 1300|26 (7.56%) ---------------------------------------------
    AnneOwl 1400|23 (6.69%) ----------------------------------------
    AnneOwl 1500|30 (8.72%) ----------------------------------------------------
    AnneOwl 1600|22 (6.40%) --------------------------------------
    AnneOwl 1700|18 (5.23%) -------------------------------
    AnneOwl 1800|32 (9.30%) --------------------------------------------------------
    AnneOwl 1900|18 (5.23%) -------------------------------
    AnneOwl 2000|12 (3.49%) ---------------------
    AnneOwl 2100|14 (4.07%) -------------------------
    AnneOwl 2200| 9 (2.62%) ----------------
    AnneOwl 2300| 8 (2.33%) --------------
"""
=======
>>>>>>> cbc04de (util to normalise timestamps)
import sys
import os

filename = sys.argv[1]
rounding_factor = int(sys.argv[2])


def round_to_multiple(number: int, multiple: int) -> int:
    return round(number / multiple) * multiple


def main() -> None:
    try:
        with open(filename, "r") as data:
            for line in data:
                user, time = line.rstrip().split(" ", 2)
                hour, minute = int(time[:2]), int(time[2:])
                rounded_hour = hour
                rounded_min = round_to_multiple(minute, rounding_factor)
                if rounded_min == 60:
                    rounded_min = 0
                    if rounded_hour == 23:
                        rounded_hour = 0
                    else:
                        rounded_hour += 1
                print(f"{user} {rounded_hour:02d}{rounded_min:02d}")
        sys.stdout.flush()
    except BrokenPipeError:
        # Python flushes standard streams on exit; redirect remaining output
        # to devnull to avoid another BrokenPipeError at shutdown
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)  # Python exits with error code 1 on EPIPE


if __name__ == "__main__":
    main()
