import tomllib
from pathlib import Path

PER_TOKENS = 1_000_000


def load_catalog(path: Path) -> dict[str, dict[str, float]]:
    with open(path, "rb") as f:
        return tomllib.load(f)["models"]


def call_cost(catalog: dict, call: dict) -> float:
    price = catalog.get(call.get("model"), {})
    return (
        call.get("input_tokens", 0) * price.get("input", 0)
        + call.get("output_tokens", 0) * price.get("output", 0)
    ) / PER_TOKENS


def trial_cost(catalog: dict, usage: list[dict]) -> float:
    return sum(call_cost(catalog, call) for call in usage)
