"""okr_core.api の単体テスト。"""
from __future__ import annotations

from pathlib import Path

import pytest

from okr_core.api import carry_over, compute_progress, connect, untagged_activities


@pytest.fixture
def api_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "okr" / "key_results").mkdir(parents=True)
    (tmp_path / "okr" / "weekly").mkdir(parents=True)
    (tmp_path / "diary" / "日記").mkdir(parents=True)
    monkeypatch.setenv("OKR_ROOT", str(tmp_path / "okr"))
    monkeypatch.setenv("NIKKI_ROOT", str(tmp_path / "diary"))
    return tmp_path


def _write_kr(tmp_path: Path, filename: str, kr_id: str, objective_id: str, title: str, progress: float = 0.0) -> None:
    path = tmp_path / "okr" / "key_results" / filename
    path.write_text(
        f"## {kr_id}\n- objective_id: {objective_id}\n- title: {title}\n- progress: {progress}\n",
        encoding="utf-8",
    )


def _write_weekly_kr(tmp_path: Path, week: str, kr_id: str, objective_id: str, title: str, progress: float = 0.0) -> None:
    path = tmp_path / "okr" / "weekly" / f"{week}.md"
    path.write_text(
        f"## {kr_id}\n- objective_id: {objective_id}\n- title: {title}\n- progress: {progress}\n",
        encoding="utf-8",
    )


def _write_diary(tmp_path: Path, date: str, activities: list[tuple[str, str, bool, str | None]]) -> None:
    """Write a diary file with activities.

    activities: list of (id, title, done, objective_id)
    """
    lines = ["### タスク"]
    for act_id, title, done, objective_id in activities:
        state = "x" if done else " "
        obj_part = f" objective_id={objective_id}" if objective_id else ""
        lines.append(f"- [{state}] {title} <!-- okr:id={act_id}{obj_part} -->")
    (tmp_path / "diary" / "日記" / f"{date}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestConnect:
    def test_links_activity_to_kr_objective(self, api_env: Path) -> None:
        _write_kr(api_env, "kr.md", "kr1", "obj1", "月次売上10%増")
        _write_diary(api_env, "2026-06-01", [("a1", "タスクA", False, None)])

        connect("a1", "kr1")

        content = (api_env / "diary" / "日記" / "2026-06-01.md").read_text(encoding="utf-8")
        assert "objective_id=obj1" in content

    def test_nonexistent_kr_raises(self, api_env: Path) -> None:
        _write_diary(api_env, "2026-06-01", [("a1", "タスクA", False, None)])

        with pytest.raises(ValueError, match="KeyResult not found: no-such-kr"):
            connect("a1", "no-such-kr")

    def test_nonexistent_activity_raises(self, api_env: Path) -> None:
        _write_kr(api_env, "kr.md", "kr1", "obj1", "月次売上10%増")

        with pytest.raises(ValueError, match="Activity not found: no-such-act"):
            connect("no-such-act", "kr1")


class TestComputeProgress:
    def test_no_activities_returns_zero(self, api_env: Path) -> None:
        _write_kr(api_env, "kr.md", "kr1", "obj1", "月次売上10%増")

        assert compute_progress("kr1") == 0.0

    def test_all_done_returns_one(self, api_env: Path) -> None:
        _write_kr(api_env, "kr.md", "kr1", "obj1", "月次売上10%増")
        _write_diary(api_env, "2026-06-01", [
            ("a1", "タスクA", True, "obj1"),
            ("a2", "タスクB", True, "obj1"),
            ("a3", "タスクC", True, "obj1"),
        ])

        assert compute_progress("kr1") == 1.0

    def test_partial_done_returns_ratio(self, api_env: Path) -> None:
        _write_kr(api_env, "kr.md", "kr1", "obj1", "月次売上10%増")
        _write_diary(api_env, "2026-06-01", [
            ("a1", "タスクA", True, "obj1"),
            ("a2", "タスクB", True, "obj1"),
            ("a3", "タスクC", False, "obj1"),
        ])

        assert compute_progress("kr1") == pytest.approx(0.667, abs=0.001)

    def test_nonexistent_kr_raises(self, api_env: Path) -> None:
        with pytest.raises(ValueError, match="KeyResult not found: no-such-kr"):
            compute_progress("no-such-kr")


class TestCarryOver:
    def test_incomplete_kr_carried_over(self, api_env: Path) -> None:
        _write_weekly_kr(api_env, "2026-W22", "kr1", "obj1", "月次売上10%増", progress=0.5)

        carried = carry_over("2026-W23")

        assert len(carried) == 1
        assert carried[0].id == "kr1-carry-2026-W23"
        assert carried[0].progress == 0.0

    def test_fully_achieved_kr_not_carried(self, api_env: Path) -> None:
        _write_weekly_kr(api_env, "2026-W22", "kr1", "obj1", "月次売上10%増", progress=1.0)

        carried = carry_over("2026-W23")

        assert carried == []

    def test_invalid_week_format_raises(self, api_env: Path) -> None:
        with pytest.raises(ValueError, match="invalid week format: 2025-99"):
            carry_over("2025-99")


class TestUntaggedActivities:
    def test_returns_only_untagged(self, api_env: Path) -> None:
        _write_diary(api_env, "2026-06-01", [
            ("a1", "タスクA", False, None),
            ("a2", "タスクB", False, None),
            ("a3", "タスクC", False, "obj1"),
        ])

        result = untagged_activities("2026-06-01", "2026-06-01")

        ids = [a.id for a in result]
        assert "a1" in ids
        assert "a2" in ids
        assert "a3" not in ids

    def test_excludes_out_of_range(self, api_env: Path) -> None:
        _write_diary(api_env, "2026-05-31", [("a1", "タスクA", False, None)])

        result = untagged_activities("2026-06-01", "2026-06-30")

        assert result == []

    def test_start_after_end_raises(self, api_env: Path) -> None:
        with pytest.raises(ValueError, match="invalid date range: 2025-01-10 .. 2025-01-01"):
            untagged_activities("2025-01-10", "2025-01-01")
