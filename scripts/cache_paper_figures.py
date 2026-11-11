"""Backward-compatible entry point for publisher figure discovery."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.discover_paper_figures import cache_figures, main, supported_image


if __name__ == "__main__":
    main()
