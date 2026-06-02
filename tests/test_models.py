"""エンティティモデルと nikki_root() のテスト。"""
from __future__ import annotations

from pathlib import Path

import pytest

from okr_core import (
    Activity,
    DailyEntry,
    KeyResult,
    Objective,
    Reflection,
    RichnessScore,
    WeeklySummary,
)
from okr_core._paths import nikki_root


class TestObjective:
    def test_top_level_objective(self) -> None:
        obj = Objective(
            id="q1",
            title="売上目標",
            parent_id=None,
            period="2026-Q3",
            category="Work",
        )
        assert obj.id == "q1"
        assert obj.title == "売上目標"
        assert obj.parent_id is None
        assert obj.period == "2026-Q3"
        assert obj.category == "Work"

    def test_child_objective(self) -> None:
        obj = Objective(
            id="q2",
            title="週次目標",
            parent_id="q1",
            period="2026-W23",
            category="Work",
        )
        assert obj.parent_id == "q1"


class TestKeyResult:
    def test_initial_progress(self) -> None:
        kr = KeyResult(
            id="kr1",
            objective_id="q1",
            title="月次売上10%増",
            progress=0.0,
        )
        assert kr.progress == 0.0


class TestActivity:
    def test_unlinked_activity(self) -> None:
        act = Activity(
            id="a1",
            date="2026-06-01",
            title="提案書作成",
            done=False,
            objective_id=None,
        )
        assert act.objective_id is None
        assert act.done is False


class TestReflection:
    def test_reflection_lists(self) -> None:
        ref = Reflection(
            id="r1",
            week="2026-W23",
            highlights=["達成A"],
            improvements=["改善B"],
            next_policy="方針C",
        )
        assert ref.highlights == ["達成A"]
        assert ref.improvements == ["改善B"]


class TestDailyEntry:
    def test_empty_activities(self) -> None:
        entry = DailyEntry(
            date="2026-06-01",
            activities=[],
            routines={},
            diary_text="",
        )
        assert entry.activities == []


class TestRichnessScore:
    def test_score_fields(self) -> None:
        score = RichnessScore(
            total=85,
            breakdown={"morning": 20, "task": 15},
        )
        assert score.total == 85
        assert score.breakdown == {"morning": 20, "task": 15}


class TestWeeklySummary:
    def test_summary_defaults(self) -> None:
        summary = WeeklySummary(
            week="2026-W23",
            scores=[],
            avg=0.0,
            max=0,
            min=0,
        )
        assert summary.avg == 0.0


class TestPackageImport:
    def test_reexports_from_package(self) -> None:
        assert Objective is not None
        assert KeyResult is not None
        assert Activity is not None
        assert Reflection is not None
        assert DailyEntry is not None
        assert RichnessScore is not None
        assert WeeklySummary is not None


class TestNikkiRoot:
    def test_returns_path_from_env(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("NIKKI_ROOT", str(tmp_path))
        assert nikki_root() == tmp_path

    def test_unset_raises_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NIKKI_ROOT", raising=False)
        with pytest.raises(ValueError, match="NIKKI_ROOT"):
            nikki_root()

    def test_empty_string_raises_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NIKKI_ROOT", "")
        with pytest.raises(ValueError, match="NIKKI_ROOT"):
            nikki_root()

    def test_whitespace_only_raises_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NIKKI_ROOT", "   ")
        with pytest.raises(ValueError, match="NIKKI_ROOT"):
            nikki_root()
