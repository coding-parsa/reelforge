"""Entry point for the packaged app (`pyinstaller` runs this file)."""
import sys

from reelforge.launcher import main

if __name__ == "__main__":
    sys.exit(main())
