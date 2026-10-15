"""Settings: runstash.toml in the project, plus optional per-user settings in
~/.config/runstash/config.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

PROJECT_FILE = "runstash.toml"
USER_FILE = Path("~/.config/runstash/config.toml")


@dataclass(frozen=True)
class Config:
    bucket: str
    prefix: str
    runs_dir: Path
    region: str = "us-east-2"


def find_project_file(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for directory in (here, *here.parents):
        if (directory / PROJECT_FILE).is_file():
            return directory / PROJECT_FILE
    raise SystemExit(f"runstash: no {PROJECT_FILE} in {here} or its parents")


def _read(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def _build(values: dict, root: Path) -> Config:
    runs_dir = Path(values.get("runs_dir", "runs")).expanduser()
    return Config(
        bucket=values["bucket"],
        prefix=values["prefix"].strip("/"),
        runs_dir=runs_dir if runs_dir.is_absolute() else root / runs_dir,
        region=values.get("region", "us-east-2"),
    )


def load_project() -> Config:
    path = find_project_file()
    return _build(_read(path), path.parent)


def load() -> Config:
    """Project settings, with anything set in the user's config file taking precedence."""
    path = find_project_file()
    values = _read(path)
    user = USER_FILE.expanduser()
    if user.is_file():
        values.update(_read(user))
    return _build(values, path.parent)
