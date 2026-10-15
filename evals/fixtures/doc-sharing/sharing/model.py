from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Account:
    id: str
    suspended: bool = False
    support: bool = False


@dataclass(frozen=True)
class Share:
    role: str  # viewer, commenter, editor
    until: date | None = None


@dataclass(frozen=True)
class Document:
    id: str
    owner_id: str
    shares: dict[str, Share] = field(default_factory=dict)  # account id -> share
