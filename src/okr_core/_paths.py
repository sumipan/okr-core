"""NIKKI_ROOT パス解決ユーティリティ。"""
from __future__ import annotations

import os
from pathlib import Path


def nikki_root() -> Path:
    """NIKKI_ROOT 環境変数の値を Path で返す。未設定なら ValueError。"""
    raw = os.environ.get("NIKKI_ROOT", "").strip()
    if not raw:
        raise ValueError(
            '環境変数 NIKKI_ROOT が未設定です。.env に NIKKI_ROOT=/path/to/nikki を追加してください。'
        )
    return Path(raw)
