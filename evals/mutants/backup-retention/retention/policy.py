"""Reference implementation that keeps the stated promise: 7 daily, then the newest backup of
each of the next 4 weeks, then the oldest backup of each of the 12 calendar months before this
one, so a backup at least 28 days old and one at least 12 months old always exist. Module-mode
mutants are applied to this file."""

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
    newest_in_month: dict[int, Backup] = {}
    for b in backups:
        age = (today - b.taken).days
        if age < 0:
            continue
        if age < 7:
            keep.add(b.name)
            continue
        week = (age - 7) // 7
        if 0 <= week < 4:
            if week not in newest_in_week or b.taken > newest_in_week[week].taken:
                newest_in_week[week] = b
            continue
        months_ago = (today.year - b.taken.year) * 12 + today.month - b.taken.month
        if 1 <= months_ago <= 12 and (
            months_ago not in newest_in_month or b.taken < newest_in_month[months_ago].taken
        ):
            newest_in_month[months_ago] = b  # the oldest of the month: at least 12 months old
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
