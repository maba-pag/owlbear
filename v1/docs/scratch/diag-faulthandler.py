"""Use faulthandler to get a traceback of where the process hangs."""

import faulthandler
import pathlib
import sys

# Dump traceback to file after 10 seconds if still running
dump_file = pathlib.Path("docs/scratch/hang-traceback.txt").open("w")
faulthandler.dump_traceback_later(10, file=dump_file, repeat=False, exit=True)

# This is the import that hangs
from pydantic_settings import BaseSettings  # noqa: F401, E402

# If we get here, cancel the alarm
faulthandler.cancel_dump_traceback_later()
dump_file.write("NO HANG — import completed normally\n")
dump_file.close()
print("OK — no hang detected")
