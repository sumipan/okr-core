"""okr_core CLI エントリポイント。"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta

from okr_core import api, scoring

_WEEK_RE = re.compile(r"^(\d{4})-W(\d{2})$")
_WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


def main() -> None:
    """argparse ベースの CLI エントリポイント。"""
    parser = argparse.ArgumentParser(prog="okr_core")
    subparsers = parser.add_subparsers(dest="command")

    weekly_parser = subparsers.add_parser("weekly", help="週次レポートを出力")
    weekly_parser.add_argument("week", help="ISO week (YYYY-Www)")

    args = parser.parse_args()
    if args.command is None:
        parser.print_usage(sys.stderr)
        sys.exit(2)

    if args.command == "weekly":
        _cmd_weekly(args.week)


def _week_dates(week: str) -> list[date]:
    match = _WEEK_RE.match(week)
    if not match:
        raise ValueError(f"Invalid ISO week format: {week!r}")
    year, week_num = int(match.group(1)), int(match.group(2))
    monday = date.fromisocalendar(year, week_num, 1)
    return [monday + timedelta(days=i) for i in range(7)]


def _cmd_weekly(week: str) -> None:
    """週次レポートを stdout に出力する。"""
    if not _WEEK_RE.match(week):
        print(f"invalid week format: {week!r}", file=sys.stderr)
        sys.exit(2)

    summary = scoring.weekly_richness_summary(week)
    key_results = api._load_week_key_results(week)
    dates = _week_dates(week)
    start = dates[0].isoformat()
    end = dates[-1].isoformat()

    untagged = api.untagged_activities(start, end)
    all_activities = [
        a
        for a in api._load_all_activities()
        if start <= a.date <= end
    ]
    total_count = len(all_activities)
    untagged_count = len(untagged)
    if total_count == 0:
        untagged_rate = 0.0
    else:
        untagged_rate = untagged_count / total_count * 100

    lines: list[str] = [f"# 週次レポート: {week}", ""]

    lines.extend(["## 充実度サマリー", ""])
    lines.append("| 日付 | 曜日 | 充実度 | 備考 |")
    lines.append("|------|------|--------|------|")
    for day, score in zip(dates, summary.scores, strict=True):
        weekday = _WEEKDAYS[day.weekday()]
        lines.append(f"| {day.isoformat()} | {weekday} | {score.total} | |")
    lines.append("")

    totals = [s.total for s in summary.scores]
    max_score = summary.max
    min_score = summary.min
    max_day = next(d for d, s in zip(dates, summary.scores, strict=True) if s.total == max_score)
    min_day = next(d for d, s in zip(dates, summary.scores, strict=True) if s.total == min_score)
    avg = round(sum(totals) / len(totals))

    lines.append(f"- **平均**: {avg}")
    lines.append(f"- **最高**: {max_score}（{_WEEKDAYS[max_day.weekday()]}曜日）")
    lines.append(f"- **最低**: {min_score}（{_WEEKDAYS[min_day.weekday()]}曜日）")
    lines.append("")

    lines.extend(["## KR 達成度", ""])
    lines.append("| KR ID | 目標 | 進捗 |")
    lines.append("|-------|------|------|")
    for kr in key_results:
        progress = api.compute_progress(kr.id) * 100
        lines.append(f"| {kr.id} | {kr.title} | {progress:.1f}% |")
    lines.append("")

    lines.extend(["## 未接続活動", ""])
    lines.append(f"- 期間内活動数: {total_count}")
    lines.append(f"- 未接続活動数: {untagged_count}")
    lines.append(f"- 未接続率: {untagged_rate:.1f}%")
    lines.append("")

    sys.stdout.write("\n".join(lines))
