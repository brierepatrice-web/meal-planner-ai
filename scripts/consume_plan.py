from __future__ import annotations

import sys


def main() -> int:
    print("consume_plan.py is retired to avoid consuming an entire week by mistake.")
    print('Use: python scripts\\consume_meal.py consume --day "Jour 1"')
    print('Other actions: cancel, postpone.')
    return 2


if __name__ == "__main__":
    sys.exit(main())
