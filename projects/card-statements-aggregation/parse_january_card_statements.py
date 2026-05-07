#!/usr/bin/env python3
"""Compatibility wrapper for the production expense processor.

The old January-only parser has been replaced by `process_expenses.py`, which
processes every supported month/source file in the Drive folder.
"""
from process_expenses import main

if __name__ == "__main__":
    main()
