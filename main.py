"""Entry point."""

import logging

import core
from web_ui import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

if __name__ == "__main__":
    core.start()
    app = create_app()
    app.run(host="0.0.0.0", port=7070, debug=False, use_reloader=False)
