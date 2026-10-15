"""Who may do what to a document. `docs/policy.md` is the promise; this file must match it."""

from __future__ import annotations

from datetime import date

from sharing.model import Account, Document

ACTIONS = ("read", "comment", "edit", "share", "delete")
ROLE_ACTIONS = {
    "viewer": frozenset({"read"}),
    "commenter": frozenset({"read", "comment"}),
    "editor": frozenset({"read", "comment", "edit"}),
    "owner": frozenset(ACTIONS),
}


def role_of(actor: Account, doc: Document, today: date) -> str | None:
    """The actor's role on the document today, or None."""
    if actor.id == doc.owner_id:
        return "owner"
    share = doc.shares.get(actor.id)
    if share is None:
        return None
    if share.until is not None and not today < share.until:
        return None
    return share.role


def can(actor: Account, action: str, doc: Document, today: date) -> bool:
    """Whether the actor may perform the action on the document today."""
    if action not in ACTIONS:
        raise ValueError(f"unknown action {action!r}")
    if actor.id == doc.owner_id:
        return True
    if actor.support:
        return action != "delete"  # support must never destroy customer data
    if actor.suspended:
        return False
    role = role_of(actor, doc, today)
    return role is not None and action in ROLE_ACTIONS[role]
