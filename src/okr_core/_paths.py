"""NIKKI_ROOT / OKR データディレクトリ解決ユーティリティ。"""
from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def nikki_root() -> Path:
    """NIKKI_ROOT 環境変数の値を Path で返す。未設定なら ValueError。"""
    raw = os.environ.get("NIKKI_ROOT", "").strip()
    if not raw:
        raise ValueError(
            '環境変数 NIKKI_ROOT が未設定です。.env に NIKKI_ROOT=/path/to/nikki を追加してください。'
        )
    return Path(raw)


def okr_root() -> Path:
    """OKR Markdown 永続化ルート（リポジトリ内 okr/ または OKR_ROOT）。"""
    raw = os.environ.get("OKR_ROOT", "").strip()
    if raw:
        return Path(raw)
    return _REPO_ROOT / "okr"
