"""Allow ``python -m darkroom`` and ``python -m darkroom.cli``."""

from darkroom.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
