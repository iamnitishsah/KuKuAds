"""Streamlit entry point:  streamlit run app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))  # run without installing the package

from kukuads.ui import main  # noqa: E402

main()
