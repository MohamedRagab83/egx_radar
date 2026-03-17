"""Tools module entry point."""

import sys

# Simple dispatcher to allow running tools
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "paper_trading_tracker":
        from egx_radar.tools.paper_trading_tracker import create_tracker
        create_tracker()
    else:
        print("Usage: python -m egx_radar.tools <tool_name>")
        print("Available tools:")
        print("  - paper_trading_tracker")
