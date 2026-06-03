"""日記エントリから充実度スコアを算出する。"""
from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta

from okr_core._paths import nikki_root
from okr_core.models import Activity, DailyEntry, RichnessScore, WeeklySummary

_ROUTINE_PREFIXES = (("朝/", 20), ("昼/", 10), ("夜/", 20))
_TASK_POINTS_EACH = 2
_TASK_POINTS_MAX = 20
_DIARY_FACTS_HEADER = (
    "## 今日あったこと（＝事実）、そのとき思ったこと（＝解釈）、そう思った理由（＝論理）"
)
_3LINE_PATTERNS = (
    r"\*\s*事実:\s*.+",
    r"\*\s*感情:\s*.+",
    r"\*\s*気づき:\s*.+",
)
_WEEK_RE = re.compile(r"^(\d{4})-W(\d{2})$")
_CHECKBOX_RE = re.compile(r"^\s*[-*]\s*\[([ xX\-])\]\s*(.+)$")


def _activity_id(title: str) -> str:
    return hashlib.sha256(title.encode()).hexdigest()[:8]


def _routine_points(routines: dict[str, bool], prefix: str, max_points: int) -> int:
    keys = [k for k in routines if k.startswith(prefix)]
    if not keys:
        return 0
    done = sum(1 for k in keys if routines[k])
    return round(done / len(keys) * max_points)


def _diary_length_points(text: str) -> int:
    length = len(text)
    if length >= 500:
        return 20
    if length >= 200:
        return 10
    return 0


def _has_3line_diary(text: str) -> bool:
    return all(re.search(pat, text) for pat in _3LINE_PATTERNS)


def calculate_richness_score(entry: DailyEntry) -> RichnessScore:
    """DailyEntry から充実度スコア（最大100点）を算出する。"""
    breakdown: dict[str, int] = {}

    morning = _routine_points(entry.routines, "朝/", 20)
    noon = _routine_points(entry.routines, "昼/", 10)
    evening = _routine_points(entry.routines, "夜/", 20)
    breakdown["朝ルーティン"] = morning
    breakdown["昼ルーティン"] = noon
    breakdown["夜ルーティン"] = evening

    task_done = sum(1 for a in entry.activities if a.done)
    task_score = min(task_done * _TASK_POINTS_EACH, _TASK_POINTS_MAX)
    breakdown["タスク完了数"] = task_score

    diary_score = _diary_length_points(entry.diary_text)
    breakdown["日記記入量"] = diary_score

    three_line = 10 if _has_3line_diary(entry.diary_text) else 0
    breakdown["3行日記"] = three_line

    total = morning + noon + evening + task_score + diary_score + three_line
    return RichnessScore(total=total, breakdown=breakdown)


def _parse_section_block(content: str, header: str) -> str:
    lines = content.splitlines()
    in_section = False
    _hm = re.match(r"^(#+)", header)
    header_level = len(_hm.group(1)) if _hm else 2
    parts: list[str] = []
    for line in lines:
        if line.strip() == header:
            in_section = True
            continue
        if in_section:
            m = re.match(r"^(#+)\s", line)
            if m and len(m.group(1)) <= header_level:
                break
            parts.append(line)
    return "\n".join(parts).strip()


def _parse_routines(content: str) -> dict[str, bool]:
    section_map = {
        "### 朝ルーティン": "朝",
        "### 昼ルーティン": "昼",
        "### 夜ルーティン": "夜",
    }
    routines: dict[str, bool] = {}
    for header, period in section_map.items():
        block = _parse_section_block(content, header)
        for line in block.splitlines():
            match = _CHECKBOX_RE.match(line)
            if not match:
                continue
            state, label = match.group(1), match.group(2).strip()
            done = state.lower() == "x"
            routines[f"{period}/{label}"] = done
    return routines


def _parse_activities(content: str, day: str) -> list[Activity]:
    activities: list[Activity] = []
    in_tasks = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped in ("### タスク", "## 今日やること"):
            in_tasks = True
            continue
        if in_tasks and stripped.startswith("###"):
            break
        if not in_tasks:
            continue
        match = _CHECKBOX_RE.match(line)
        if not match:
            continue
        state, rest = match.group(1), match.group(2)
        done = state.lower() == "x"
        title = rest.strip()
        activities.append(
            Activity(
                id=_activity_id(title),
                date=day,
                title=title,
                done=done,
            )
        )
    return activities


def _parse_diary(d: str, content: str) -> DailyEntry:
    """日記 Markdown を DailyEntry に変換する。"""
    facts = _parse_section_block(content, _DIARY_FACTS_HEADER)
    three_line = _parse_section_block(content, "## 3行日記")
    diary_parts = [p for p in (facts, three_line) if p]
    return DailyEntry(
        date=d,
        activities=_parse_activities(content, d),
        routines=_parse_routines(content),
        diary_text="\n".join(diary_parts),
    )


def _week_dates(week: str) -> list[str]:
    match = _WEEK_RE.match(week)
    if not match:
        raise ValueError(f"Invalid ISO week format: {week!r}")
    year, week_num = int(match.group(1)), int(match.group(2))
    monday = date.fromisocalendar(year, week_num, 1)
    return [(monday + timedelta(days=i)).isoformat() for i in range(7)]


def weekly_richness_summary(week: str) -> WeeklySummary:
    """ISO 週文字列から7日分の充実度サマリーを返す。"""
    diary_dir = nikki_root() / "日記"
    scores: list[RichnessScore] = []
    for day in _week_dates(week):
        path = diary_dir / f"{day}.md"
        if path.is_file():
            entry = _parse_diary(day, path.read_text(encoding="utf-8"))
            scores.append(calculate_richness_score(entry))
        else:
            scores.append(RichnessScore(total=0, breakdown={}))
    totals = [s.total for s in scores]
    return WeeklySummary(
        week=week,
        scores=scores,
        avg=sum(totals) / len(totals),
        max=max(totals),
        min=min(totals),
    )
