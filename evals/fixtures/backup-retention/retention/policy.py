"""Which backups to keep and which to delete.

Policy: keep every backup from the last 7 days, the newest backup of each of the last 4 weeks,
and the newest backup of each of the last 12 months. Everything else is deleted. A deleted
backup cannot be recovered.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Backup:
    name: str
    taken: date


def keep_set(backups: list[Backup], today: date) -> set[str]:
    """Names of the backups the policy keeps."""
    keep: set[str] = set()
    newest_in_week: dict[int, Backup] = {}
    newest_in_month: dict[tuple[int, int], Backup] = {}
    for b in backups:
        age = (today - b.taken).days
        if age < 0:
            continue
        if age < 7:
            keep.add(b.name)
        week = age // 7
        if week < 4 and (week not in newest_in_week or b.taken > newest_in_week[week].taken):
            newest_in_week[week] = b
        month = (b.taken.year, b.taken.month)
        months_ago = (today.year - b.taken.year) * 12 + today.month - b.taken.month
        if months_ago < 12 and (month not in newest_in_month or b.taken > newest_in_month[month].taken):
            newest_in_month[month] = b
    keep.update(b.name for b in newest_in_week.values())
    keep.update(b.name for b in newest_in_month.values())
    return keep


def to_delete(backups: list[Backup], today: date) -> list[Backup]:
    """Backups the policy does not keep, oldest first."""
    kept = keep_set(backups, today)
    return sorted((b for b in backups if b.name not in kept), key=lambda b: b.taken)


def oldest_kept(backups: list[Backup], today: date) -> Backup | None:
    kept = keep_set(backups, today)
    candidates = [b for b in backups if b.name in kept]
    return min(candidates, key=lambda b: b.taken) if candidates else None


def cutoff(today: date) -> date:
    """Nothing newer than this date is ever deleted."""
    return today - timedelta(days=6)
