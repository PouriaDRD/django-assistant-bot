from __future__ import annotations

import asyncio

from django_assistant_bot.application import run


def main() -> None:
    """
    Application command-line entrypoint.
    """

    try:
        asyncio.run(run())

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
