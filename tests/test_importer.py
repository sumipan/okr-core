"""import_goals() のテスト。"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from okr_core.importer import import_goals


def _obj_id(title: str) -> str:
    return hashlib.sha256(title.encode()).hexdigest()[:8]


class TestImportGoals:
    def test_imports_objectives_from_markdown(self, tmp_path: Path) -> None:
        goals_dir = tmp_path / "目標"
        goals_dir.mkdir()
        (goals_dir / "2026-Q2.md").write_text(
            "- [ ] 事業計画を策定する\n",
            encoding="utf-8",
        )
        result = import_goals(goals_dir)
        assert len(result) == 1
        assert result[0].title == "事業計画を策定する"
        assert result[0].period == "2026-Q2"

    def test_work_category(self, tmp_path: Path) -> None:
        goals_dir = tmp_path / "目標"
        goals_dir.mkdir()
        (goals_dir / "2026-Q2.md").write_text(
            "- [ ] 事業計画を策定する\n",
            encoding="utf-8",
        )
        result = import_goals(goals_dir)
        assert result[0].category == "Work"

    def test_home_category(self, tmp_path: Path) -> None:
        goals_dir = tmp_path / "目標"
        goals_dir.mkdir()
        (goals_dir / "2026-Q2.md").write_text(
            "- [ ] 健康管理を続ける\n",
            encoding="utf-8",
        )
        result = import_goals(goals_dir)
        assert result[0].category == "Home"

    def test_other_category(self, tmp_path: Path) -> None:
        goals_dir = tmp_path / "目標"
        goals_dir.mkdir()
        (goals_dir / "2026-Q2.md").write_text(
            "- [ ] 趣味の読書を増やす\n",
            encoding="utf-8",
        )
        result = import_goals(goals_dir)
        assert result[0].category == "Other"

    def test_parent_id_from_indent(self, tmp_path: Path) -> None:
        goals_dir = tmp_path / "目標"
        goals_dir.mkdir()
        (goals_dir / "2026-Q2.md").write_text(
            "- [ ] 親タスク\n"
            "  - [ ] 子タスク\n",
            encoding="utf-8",
        )
        result = import_goals(goals_dir)
        parent = next(o for o in result if o.title == "親タスク")
        child = next(o for o in result if o.title == "子タスク")
        assert parent.parent_id is None
        assert child.parent_id == parent.id

    def test_deterministic_id(self, tmp_path: Path) -> None:
        goals_dir = tmp_path / "目標"
        goals_dir.mkdir()
        (goals_dir / "2026-Q2.md").write_text(
            "- [ ] 同じタイトル\n",
            encoding="utf-8",
        )
        first = import_goals(goals_dir)[0].id
        second = import_goals(goals_dir)[0].id
        assert first == second == _obj_id("同じタイトル")

    def test_missing_goals_dir_returns_empty(self, tmp_path: Path) -> None:
        assert import_goals(tmp_path / "nonexistent") == []

    def test_no_md_files_returns_empty(self, tmp_path: Path) -> None:
        goals_dir = tmp_path / "目標"
        goals_dir.mkdir()
        assert import_goals(goals_dir) == []

    def test_completed_tasks_excluded(self, tmp_path: Path) -> None:
        goals_dir = tmp_path / "目標"
        goals_dir.mkdir()
        (goals_dir / "2026-Q2.md").write_text(
            "- [x] 完了済み\n"
            "- [ ] 未完了\n",
            encoding="utf-8",
        )
        result = import_goals(goals_dir)
        titles = [o.title for o in result]
        assert "完了済み" not in titles
        assert "未完了" in titles

    def test_uses_latest_file_by_name(self, tmp_path: Path) -> None:
        goals_dir = tmp_path / "目標"
        goals_dir.mkdir()
        (goals_dir / "2026-Q1.md").write_text("- [ ] 古い\n", encoding="utf-8")
        (goals_dir / "2026-Q2.md").write_text("- [ ] 新しい\n", encoding="utf-8")
        result = import_goals(goals_dir)
        assert len(result) == 1
        assert result[0].title == "新しい"
        assert result[0].period == "2026-Q2"
