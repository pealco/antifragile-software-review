"""Delete the backups the policy no longer keeps."""

from __future__ import annotations

import logging
from datetime import date

from retention.policy import Backup, to_delete

log = logging.getLogger(__name__)


class Store:
    """Backup storage. `delete` is final."""

    def list_backups(self) -> list[Backup]:
        raise NotImplementedError

    def delete(self, name: str) -> None:
        raise NotImplementedError


def prune(store: Store, today: date, dry_run: bool = False) -> list[str]:
    backups = store.list_backups()
    doomed = to_delete(backups, today)
    if len(doomed) == len(backups) and backups:
        raise RuntimeError("refusing to delete every backup")
    names = []
    for b in doomed:
        if not dry_run:
            store.delete(b.name)
        names.append(b.name)
    log.info("pruned %d of %d backups", len(names), len(backups))
    return names
