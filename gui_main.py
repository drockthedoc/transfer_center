#!/usr/bin/env python3
"""
Texas Children's Hospital Transfer Center GUI Application

This is the main entry point for the GUI application that allows interaction
with the pediatric hospital transfer decision support system.
"""
from src.gui.main_window import main
import os
import sys

# Ensure the directory containing this script is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    main()
