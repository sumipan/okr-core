"""OKR ドメインエンティティの dataclass 定義。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Objective:
    id: str
    title: str
    period: str
    category: str
    parent_id: str | None = None


@dataclass
class KeyResult:
    id: str
    objective_id: str
    title: str
    progress: float = 0.0


@dataclass
class Activity:
    id: str
    date: str
    title: str
    done: bool = False
    objective_id: str | None = None


@dataclass
class Reflection:
    id: str
    week: str
    highlights: list[str]
    improvements: list[str]
    next_policy: str


@dataclass
class DailyEntry:
    date: str
    activities: list[Activity]
    routines: dict[str, bool]
    diary_text: str


@dataclass
class RichnessScore:
    total: int
    breakdown: dict[str, int]


@dataclass
class WeeklySummary:
    week: str
    scores: list[RichnessScore]
    avg: float
    max: int
    min: int
