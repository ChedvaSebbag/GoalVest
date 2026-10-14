"""מוסיף את backend ו-core ל-path כדי שאפשר להריץ python -m agent משורש ה-Repo."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _path in (_ROOT / "backend", _ROOT / "core", _ROOT):
    _text = str(_path)
    if _text not in sys.path:
        sys.path.insert(0, _text)
