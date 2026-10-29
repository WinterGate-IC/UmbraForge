"""Allow ``python -m umbraforge`` to start the studio."""

from .app import main

if __name__ == "__main__":
    raise SystemExit(main())
