"""Package entry point for `python -m egx_radar`."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from egx_radar.ui.main_window import main


if __name__ == "__main__":
    main()
