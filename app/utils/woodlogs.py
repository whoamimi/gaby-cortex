""" utils/woodlogs.py

Sets up loggers with same format as uvicorn & combines all logging config.
https://last9.io/blog/python-logging-best-practices/
"""

import sys
import logging
import uvicorn.logging

def configure_logger(debug: bool) -> None:
    """ Configures root logger. """

    level = logging.DEBUG if debug else logging.INFO
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid duplicates in reloader/notebooks, etc.
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(
        uvicorn.logging.ColourizedFormatter(
            fmt="%(levelprefix)s %(filename)s:%(lineno)d - %(message)s",
            use_colors=sys.stdout.isatty(),
        )
    )

    root.addHandler(handler)

def setup_logger(name: str) -> logging.Logger:
    """ Universal Logger setup matching uvicorn format. """

    return logging.getLogger(name if name else __name__)
