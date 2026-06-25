"""
Hugging Face Streamlit Space entry point.
Direct mode runs the LangGraph workflow in-process (no separate API).
"""
import os
from pathlib import Path
import runpy

os.environ.setdefault("GIFT_AGENT_DIRECT", "true")

runpy.run_path(str(Path(__file__).parent / "ui" / "review_app.py"), run_name="__main__")
