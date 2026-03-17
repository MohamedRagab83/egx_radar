"""EGX Capital Flow Radar — entry point."""

import logging

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from egx_radar.ui.main_window import main

if __name__ == "__main__":
    main()
