"""``python -m owlbear_delivery_next``: every process starts through the one dispatcher (TD-173)."""

import sys

from owlbear_delivery_next.commands.dispatch import main

sys.exit(main())
