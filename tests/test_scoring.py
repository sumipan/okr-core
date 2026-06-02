"""scoring モジュールのテスト。"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from okr_core.models import Activity, DailyEntry, RichnessScore
from okr_core.scoring import calculate_richness_score, weekly_richness_summary


def _perfect_entry() -> DailyEntry:
    return DailyEntry(
        date="2026-06-02",
        activities=[
            Activity(
                id=f"t{i}",
                date="2026-06-02",
                title=f"タスク{i}",
                done=True,
            )
            for i in range(10)
        ],
        routines={
            "朝/散歩": True,
            "昼/ストレッチ": True,
            "夜/腹筋": True,
        },
        diary_text="x" * 500 + "\n* 事実: あった\n* 感情: よかった\n* 気づき: 学び",
    )


class TestCalculateRichnessScore:
    def test_perfect_score_is_100(self) -> None:
        score = calculate_richness_score(_perfect_entry())
        assert score.total == 100

    def test_empty_entry_is_zero(self) -> None:
        entry = DailyEntry(date="2026-06-02", activities=[], routines={}, diary_text="")
        score = calculate_richness_score(entry)
        assert score.total == 0

    def test_task_score_capped_at_20(self) -> None:
        entry = DailyEntry(
            date="2026-06-02",
            activities=[
                Activity(
                    id=f"t{i}",
                    date="2026-06-02",
                    title=f"タスク{i}",
                    done=True,
                )
                for i in range(11)
            ],
            routines={},
            diary_text="",
        )
        score = calculate_richness_score(entry)
        assert score.breakdown["タスク完了数"] == 20

    def test_diary_200_chars_scores_10(self) -> None:
        entry = DailyEntry(
            date="2026-06-02",
            activities=[],
            routines={},
            diary_text="a" * 200,
        )
        score = calculate_richness_score(entry)
        assert score.breakdown["日記記入量"] == 10

    def test_diary_199_chars_scores_0(self) -> None:
        entry = DailyEntry(
            date="2026-06-02",
            activities=[],
            routines={},
            diary_text="a" * 199,
        )
        score = calculate_richness_score(entry)
        assert score.breakdown["日記記入量"] == 0

    def test_empty_routines_no_division_error(self) -> None:
        entry = DailyEntry(date="2026-06-02", activities=[], routines={}, diary_text="")
        score = calculate_richness_score(entry)
        assert score.breakdown["朝ルーティン"] == 0
        assert score.breakdown["昼ルーティン"] == 0
        assert score.breakdown["夜ルーティン"] == 0


class TestWeeklyRichnessSummary:
    def _week_dates(self, week: str) -> list[str]:
        m = __import__("re").match(r"^(\d{4})-W(\d{2})$", week)
        assert m
        year, week_num = int(m.group(1)), int(m.group(2))
        monday = date.fromisocalendar(year, week_num, 1)
        return [(monday + timedelta(days=i)).isoformat() for i in range(7)]

    def test_returns_seven_scores_and_stats(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("NIKKI_ROOT", str(tmp_path))
        diary_dir = tmp_path / "日記"
        diary_dir.mkdir()
        week = "2026-W23"
        dates = self._week_dates(week)
        for i, d in enumerate(dates):
            if i == 0:
                (diary_dir / f"{d}.md").write_text(
                    "### 朝ルーティン\n- [x] 散歩\n"
                    "### 昼ルーティン\n- [x] ストレッチ\n"
                    "### 夜ルーティン\n- [x] 腹筋\n"
                    "### タスク\n"
                    + "\n".join(f"- [x] タスク{j}" for j in range(10))
                    + "\n"
                    "## 今日あったこと（＝事実）、そのとき思ったこと（＝解釈）、そう思った理由（＝論理）\n"
                    + ("x" * 500)
                    + "\n## 3行日記\n* 事実: a\n* 感情: b\n* 気づき: c\n",
                    encoding="utf-8",
                )
        summary = weekly_richness_summary(week)
        assert len(summary.scores) == 7
        assert summary.week == week
        assert summary.max == 100
        assert summary.min == 0
        assert 0 < summary.avg < 100

    def test_missing_diary_file_scores_zero(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("NIKKI_ROOT", str(tmp_path))
        (tmp_path / "日記").mkdir()
        summary = weekly_richness_summary("2026-W23")
        assert len(summary.scores) == 7
        assert all(s.total == 0 for s in summary.scores)
        assert summary.avg == 0.0
        assert summary.max == 0
        assert summary.min == 0
