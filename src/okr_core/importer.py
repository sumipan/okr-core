"""目標 Markdown から Objective リストを生成する。"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from okr_core._paths import nikki_root
from okr_core.models import Objective

_WORK_KEYWORDS = ["監査", "コルクラボ", "事業", "仕事", "業務", "プロジェクト", "pj", "PJ"]
_HOME_KEYWORDS = ["身体", "生活", "健康", "お金", "家", "整える", "ウォーキング"]

_TASK_RE = re.compile(r"^(\s*)[-*]\s*\[ \]\s*(.+)$")


def _objective_id(title: str) -> str:
    return hashlib.sha256(title.encode()).hexdigest()[:8]


def _classify_category(title: str) -> str:
    if any(kw in title for kw in _WORK_KEYWORDS):
        return "Work"
    if any(kw in title for kw in _HOME_KEYWORDS):
        return "Home"
    return "Other"


def import_goals(goals_dir: Path | None = None) -> list[Objective]:
    """目標ディレクトリの最新 Markdown から未完了タスクを Objective として返す。"""
    root = goals_dir if goals_dir is not None else nikki_root() / "目標"
    if not root.is_dir():
        return []

    md_files = sorted(root.glob("*.md"), key=lambda p: p.name, reverse=True)
    if not md_files:
        return []

    latest = md_files[0]
    period = latest.stem
    content = latest.read_text(encoding="utf-8")

    stack: list[tuple[int, str]] = []
    objectives: list[Objective] = []

    for line in content.splitlines():
        match = _TASK_RE.match(line)
        if not match:
            continue
        indent_str, title = match.group(1), match.group(2).strip()
        indent = len(indent_str.expandtabs())

        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent_id = stack[-1][1] if stack else None

        obj_id = _objective_id(title)
        objectives.append(
            Objective(
                id=obj_id,
                title=title,
                period=period,
                category=_classify_category(title),
                parent_id=parent_id,
            )
        )
        stack.append((indent, obj_id))

    return objectives
