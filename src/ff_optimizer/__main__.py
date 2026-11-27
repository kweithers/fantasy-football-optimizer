"""Allow running the package via `python -m ff_optimizer`."""

import sys

from ff_optimizer.cli import main

if __name__ == "__main__":
    sys.exit(main())
