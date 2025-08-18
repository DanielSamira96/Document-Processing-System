import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "code"))

from ui.streamlit_app import DocumentProcessorUI

def main():
    app = DocumentProcessorUI()
    app.run()

if __name__ == "__main__":
    main()