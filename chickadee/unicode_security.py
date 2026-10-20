"""Pinned, restricted UTS #39 data; never fetch character data at runtime."""
import json
from pathlib import Path

DATA = json.loads((Path(__file__).with_name('data') / 'confusables-ascii.json').read_text(encoding='utf-8'))
TABLE = str.maketrans(DATA['mapping'])


def fold_letters(text):
    return text.translate(TABLE)
