"""Compatibility Windows installer entry point."""
import sys
from sias_autologin.platforms.windows.installer import *

if __name__ == "__main__":
    sys.exit(entrypoint())
