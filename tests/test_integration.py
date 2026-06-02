"""エンドツーエンド統合テスト。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from okr_core import api
from okr_core.api import carry_over, compute_progress, connect
from okr_core.importer import import_goals
from okr_core.scoring import weekly_richness_summary

_DIARY_TEMPLATE = """\
### 朝ルーティン
- [x] 散歩
- [x] 瞑想

### 昼ルーティン
- [x] ストレッチ

### 夜ルーティン
- [x] 腹筋
- [x] 読書

### タスク
- [x] タスクA <!-- okr:id=a1 -->
- [x] タスクB <!-- okr:id=a2 -->
- [ ] タスクC <!-- okr:id=a3 -->

## 今日あったこと（＝事実）、そのとき思ったこと（＝解釈）、そう思った理由（＝論理）

今日は朝から集中できた。プロジェクトの進捗が良く、チームとの連携もスムーズだった。午後はレビュー会議があり、フィードバックを反映する方針が固まった。夕方はドキュメント整理を進め、明日のタスクも明確になった。振り返ると充実した一日だった。（200文字以上）

## 3行日記

* 事実: プロジェクト会議で方針決定
* 感情: 達成感があった
* 気づき: 早朝の集中時間が有効
"""

_WEEK_DATES = [
    "2026-06-02",
    "2026-06-03",
    "2026-06-04",
    "2026-06-05",
    "2026-06-06",
    "2026-06-07",
    "2026-06-08",
]


@pytest.fixture
def integration_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """統合テスト用の diary / okr ディレクトリを構築する。"""
    diary_root = tmp_path / "diary"
    diary_dir = diary_root / "日記"
    diary_dir.mkdir(parents=True)
    goals_dir = diary_root / "目標"
    goals_dir.mkdir()
    (goals_dir / "2026-Q3.md").write_text(
        "- [ ] Work目標\n- [ ] Home目標\n- [ ] Other目標\n",
        encoding="utf-8",
    )

    for day in _WEEK_DATES:
        (diary_dir / f"{day}.md").write_text(_DIARY_TEMPLATE, encoding="utf-8")

    okr_root = tmp_path / "okr"
    weekly_dir = okr_root / "weekly"
    weekly_dir.mkdir(parents=True)
    (weekly_dir / "2026-W23.md").write_text(
        "## kr1\n- objective_id: obj1\n- title: 月次売上10%増\n- progress: 0.5\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("NIKKI_ROOT", str(diary_root))
    monkeypatch.setenv("OKR_ROOT", str(okr_root))
    monkeypatch.setattr("okr_core._paths._REPO_ROOT", tmp_path)
    return {"diary_root": diary_root, "okr_root": okr_root}


def _subprocess_env(integration_env: dict[str, Path], src_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["NIKKI_ROOT"] = str(integration_env["diary_root"])
    env["OKR_ROOT"] = str(integration_env["okr_root"])
    env["PYTHONPATH"] = str(src_root)
    return env


class TestFullPipeline:
    def test_full_pipeline(self, integration_env: dict[str, Path]) -> None:
        objectives = import_goals(integration_env["diary_root"] / "目標")
        assert len(objectives) == 3

        krs = api._load_week_key_results("2026-W23")
        assert len(krs) == 1
        assert krs[0].id == "kr1"

        connect("a1", "kr1")
        progress = compute_progress("kr1")
        assert progress == 1.0

        carried = carry_over("2026-W24")
        assert len(carried) == 1
        assert carried[0].progress == 0.0

        summary = weekly_richness_summary("2026-W23")
        assert summary.avg >= 0
        assert summary.max >= 0
        assert summary.min >= 0


class TestCliWeekly:
    def test_cli_weekly_output(
        self, integration_env: dict[str, Path], tmp_path: Path
    ) -> None:
        src_root = Path(__file__).resolve().parents[1] / "src"
        result = subprocess.run(
            [sys.executable, "-m", "okr_core", "weekly", "2026-W23"],
            capture_output=True,
            text=True,
            env=_subprocess_env(integration_env, src_root),
            cwd=tmp_path,
        )
        assert result.returncode == 0
        out = result.stdout
        assert "## 充実度サマリー" in out
        assert "## KR 達成度" in out
        assert "## 未接続活動" in out
        data_rows = [
            line
            for line in out.splitlines()
            if line.startswith("| 2026-")
        ]
        assert len(data_rows) == 7
        assert "| kr1 |" in out

    def test_cli_invalid_week(self, tmp_path: Path) -> None:
        src_root = Path(__file__).resolve().parents[1] / "src"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(src_root)
        env["NIKKI_ROOT"] = str(tmp_path / "diary")
        env["OKR_ROOT"] = str(tmp_path / "okr")
        (tmp_path / "diary" / "日記").mkdir(parents=True)
        (tmp_path / "okr" / "weekly").mkdir(parents=True)

        result = subprocess.run(
            [sys.executable, "-m", "okr_core", "weekly", "invalid"],
            capture_output=True,
            text=True,
            env=env,
            cwd=tmp_path,
        )
        assert result.returncode != 0

    def test_empty_week(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        diary_root = tmp_path / "diary"
        (diary_root / "日記").mkdir(parents=True)
        okr_root = tmp_path / "okr"
        (okr_root / "weekly").mkdir(parents=True)

        monkeypatch.setenv("NIKKI_ROOT", str(diary_root))
        monkeypatch.setenv("OKR_ROOT", str(okr_root))

        src_root = Path(__file__).resolve().parents[1] / "src"
        result = subprocess.run(
            [sys.executable, "-m", "okr_core", "weekly", "2026-W23"],
            capture_output=True,
            text=True,
            env=_subprocess_env(
                {"diary_root": diary_root, "okr_root": okr_root},
                src_root,
            ),
            cwd=tmp_path,
        )
        assert result.returncode == 0
        out = result.stdout
        data_rows = [
            line
            for line in out.splitlines()
            if line.startswith("| 20")
            and "| 0 |" in line
        ]
        assert len(data_rows) == 7
        assert "| kr1 |" not in out
        assert "0.0%" in out
