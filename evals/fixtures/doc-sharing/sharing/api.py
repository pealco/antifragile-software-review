"""The one path through which actions on documents happen: decide, record, then act."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date

from sharing.model import Account, Document
from sharing.policy import can

log = logging.getLogger(__name__)


class Forbidden(PermissionError):
    pass


class Audit:
    def record(self, actor_id: str, action: str, doc_id: str, allowed: bool) -> None:
        raise NotImplementedError


def perform(
    actor: Account,
    action: str,
    doc: Document,
    today: date,
    audit: Audit,
    do: Callable[[], object],
) -> object:
    """Check the policy, record the decision, then run `do()` if allowed."""
    allowed = can(actor, action, doc, today)
    audit.record(actor.id, action, doc.id, allowed)
    if not allowed:
        raise Forbidden(f"{actor.id} may not {action} {doc.id}")
    return do()
