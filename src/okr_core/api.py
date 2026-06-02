"""okr_core.api — コア API（connect / compute_progress / carry_over / untagged_activities）."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path

from okr_core import _paths
from okr_core.models import Activity, KeyResult

_WEEK_RE = re.compile(r"^(\d{4})-W(\d{2})$")
_KR_FIELD_RE = re.compile(r"^-\s+(objective_id|title|progress):\s*(.+)\s*$", re.MULTILINE)
_ACTIVITY_META_RE = re.compile(
    r"<!--\s*okr:id=(\S+?)(?:\s+objective_id=(\S+?))?\s*-->"
)


def connect(activity_id: str, key_result_id: str) -> None:
    """Activity の objective_id を KR の objective_id に設定する。"""
    kr = _load_key_result(key_result_id)
    if kr is None:
        raise ValueError(f"KeyResult not found: {key_result_id}")

    path, line_idx, activity = _find_activity(activity_id)
    if activity is None:
        raise ValueError(f"Activity not found: {activity_id}")

    activity.objective_id = kr.objective_id
    _write_activity_line(path, line_idx, activity)


def compute_progress(key_result_id: str) -> float:
    """KR の objective_id に紐づく Activity の done 比率を返す。"""
    kr = _load_key_result(key_result_id)
    if kr is None:
        raise ValueError(f"KeyResult not found: {key_result_id}")

    activities = [
        a
        for a in _load_all_activities()
        if a.objective_id == kr.objective_id
    ]
    if not activities:
        return 0.0
    done_count = sum(1 for a in activities if a.done)
    return done_count / len(activities)


def carry_over(week: str) -> list[KeyResult]:
    """前週の未達 KR（progress < 1.0）を今週 KR として複製する。"""
    _validate_week(week)
    prev_week = _previous_week(week)
    source = _load_week_key_results(prev_week)
    incomplete = [kr for kr in source if kr.progress < 1.0]

    carried: list[KeyResult] = []
    for kr in incomplete:
        new_id = f"{kr.id}-carry-{week}"
        carried.append(
            KeyResult(
                id=new_id,
                objective_id=kr.objective_id,
                title=kr.title,
                progress=0.0,
            )
        )

    if carried:
        existing = _load_week_key_results(week)
        _save_week_key_results(week, existing + carried)
    return carried


def untagged_activities(start: str, end: str) -> list[Activity]:
    """期間内で objective_id が None の Activity を返す。"""
    start_d = _parse_date(start)
    end_d = _parse_date(end)
    if start_d > end_d:
        raise ValueError(f"invalid date range: {start} .. {end}")

    return [
        a
        for a in _load_all_activities()
        if a.objective_id is None and start_d <= _parse_date(a.date) <= end_d
    ]


def _validate_week(week: str) -> None:
    if not _WEEK_RE.match(week):
        raise ValueError(f"invalid week format: {week}")


def _previous_week(week: str) -> str:
    m = _WEEK_RE.match(week)
    assert m is not None
    year, wnum = int(m.group(1)), int(m.group(2))
    monday = date.fromisocalendar(year, wnum, 1)
    prev_monday = monday - timedelta(days=7)
    py, pw, _ = prev_monday.isocalendar()
    return f"{py}-W{pw:02d}"


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _weekly_path(week: str) -> Path:
    _paths.okr_root().joinpath("weekly").mkdir(parents=True, exist_ok=True)
    return _paths.okr_root() / "weekly" / f"{week}.md"


def _load_week_key_results(week: str) -> list[KeyResult]:
    path = _weekly_path(week)
    if not path.is_file():
        return []
    return _parse_key_results_markdown(path.read_text(encoding="utf-8"))


def _save_week_key_results(week: str, key_results: list[KeyResult]) -> None:
    path = _weekly_path(week)
    path.write_text(_format_key_results_markdown(key_results), encoding="utf-8")


def _load_key_result(kr_id: str) -> KeyResult | None:
    weekly_dir = _paths.okr_root() / "weekly"
    if weekly_dir.is_dir():
        for path in sorted(weekly_dir.glob("*.md")):
            for kr in _parse_key_results_markdown(path.read_text(encoding="utf-8")):
                if kr.id == kr_id:
                    return kr
    kr_dir = _paths.okr_root() / "key_results"
    if kr_dir.is_dir():
        for path in sorted(kr_dir.glob("*.md")):
            for kr in _parse_key_results_markdown(path.read_text(encoding="utf-8")):
                if kr.id == kr_id:
                    return kr
    return None


def _parse_key_results_markdown(text: str) -> list[KeyResult]:
    results: list[KeyResult] = []
    sections = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    for section in sections:
        section = section.strip()
        if not section.startswith("## "):
            continue
        header, _, body = section.partition("\n")
        kr_id = header[3:].strip()
        fields: dict[str, str] = {}
        for match in _KR_FIELD_RE.finditer(body):
            fields[match.group(1)] = match.group(2).strip()
        if "objective_id" not in fields or "title" not in fields:
            continue
        progress = float(fields.get("progress", "0.0"))
        results.append(
            KeyResult(
                id=kr_id,
                objective_id=fields["objective_id"],
                title=fields["title"],
                progress=progress,
            )
        )
    return results


def _format_key_results_markdown(key_results: list[KeyResult]) -> str:
    lines: list[str] = []
    for kr in key_results:
        lines.extend(
            [
                f"## {kr.id}",
                f"- objective_id: {kr.objective_id}",
                f"- title: {kr.title}",
                f"- progress: {kr.progress}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + ("\n" if lines else "")


def _diary_dir() -> Path:
    return _paths.nikki_root() / "日記"


def _load_all_activities() -> list[Activity]:
    diary = _diary_dir()
    if not diary.is_dir():
        return []
    activities: list[Activity] = []
    for path in sorted(diary.glob("*.md")):
        day = path.stem
        try:
            _parse_date(day)
        except ValueError:
            continue
        activities.extend(_parse_activities_from_diary(path.read_text(encoding="utf-8"), day))
    return activities


def _parse_activities_from_diary(text: str, day: str) -> list[Activity]:
    activities: list[Activity] = []
    in_tasks = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in ("### タスク", "## 今日やること"):
            in_tasks = True
            continue
        if in_tasks and stripped.startswith("###"):
            break
        if not in_tasks:
            continue
        match = re.match(r"^- \[([ xX\-])\] (.+)$", line)
        if not match:
            continue
        state, rest = match.group(1), match.group(2)
        done = state.lower() == "x"
        meta = _ACTIVITY_META_RE.search(rest)
        if not meta:
            continue
        act_id = meta.group(1)
        objective_id = meta.group(2)
        title = _ACTIVITY_META_RE.sub("", rest).strip()
        activities.append(
            Activity(
                id=act_id,
                date=day,
                title=title,
                done=done,
                objective_id=objective_id,
            )
        )
    return activities


def _find_activity(activity_id: str) -> tuple[Path, int, Activity | None]:
    diary = _diary_dir()
    if not diary.is_dir():
        return Path(), -1, None
    for path in sorted(diary.glob("*.md")):
        day = path.stem
        try:
            _parse_date(day)
        except ValueError:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        in_tasks = False
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped in ("### タスク", "## 今日やること"):
                in_tasks = True
                continue
            if in_tasks and stripped.startswith("###"):
                break
            if not in_tasks:
                continue
            match = re.match(r"^- \[([ xX\-])\] (.+)$", line)
            if not match:
                continue
            meta = _ACTIVITY_META_RE.search(line)
            if meta and meta.group(1) == activity_id:
                state, rest = match.group(1), match.group(2)
                activity = Activity(
                    id=activity_id,
                    date=day,
                    title=_ACTIVITY_META_RE.sub("", rest).strip(),
                    done=state.lower() == "x",
                    objective_id=meta.group(2),
                )
                return path, idx, activity
    return Path(), -1, None


def _write_activity_line(path: Path, line_idx: int, activity: Activity) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    line = lines[line_idx]
    match = re.match(r"^(- \[[ xX\-]\] )(.+)$", line)
    if not match:
        raise ValueError(f"malformed activity line: {line}")
    prefix, rest = match.group(1), match.group(2)
    title = _ACTIVITY_META_RE.sub("", rest).strip()
    obj_part = (
        f" objective_id={activity.objective_id}" if activity.objective_id else ""
    )
    lines[line_idx] = f"{prefix}{title} <!-- okr:id={activity.id}{obj_part} -->"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
