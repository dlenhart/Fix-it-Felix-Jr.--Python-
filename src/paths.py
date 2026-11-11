"""Filesystem locations: the project root, the extracted assets and the score file."""

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(PROJECT_ROOT, "Data")
SCORES_FILE = os.path.join(PROJECT_ROOT, "scores.dat")
