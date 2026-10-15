import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Arm:
    name: str
    via_proxy: bool
    model: str


@dataclass(frozen=True)
class Settings:
    proxy_url: str
    proxy_policy: str
    provider_url: str
    arms: dict[str, Arm]
    agent_command: str
    agent_timeout_s: int
    workers: int
    prices_path: Path


def load(path: Path = ROOT / "scoreboard.toml") -> Settings:
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    arms = {
        name: Arm(name=name, via_proxy=spec.get("via_proxy", False), model=spec["model"])
        for name, spec in raw["arms"].items()
    }
    return Settings(
        proxy_url=raw["proxy"]["url"],
        proxy_policy=raw["proxy"].get("policy", "balanced"),
        provider_url=raw["provider"]["url"],
        arms=arms,
        agent_command=raw["agent"]["command"],
        agent_timeout_s=raw["agent"].get("timeout_s", 1800),
        workers=raw["agent"].get("workers", 4),
        prices_path=ROOT / raw["report"]["prices"],
    )
