"""File scanner module."""
import os
from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

def scan_directory(directory):
    files = []
    for root, dirs, filenames in os.walk(directory):
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                files.append(os.path.join(root, fname))
    return sorted(files)
