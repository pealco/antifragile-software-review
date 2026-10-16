#!/usr/bin/env python3
"""Validate release and skill-package invariants."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "hardening-review"
README = ROOT / "README.md"
SKILL = SKILL_DIR / "SKILL.md"
VERSION = ROOT / "VERSION"
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
SCANNER = SKILL_DIR / "scripts" / "fragility_scan.py"
RULES = SKILL_DIR / "references" / "scanner-rules.md"
WORKFLOW = ROOT / ".github" / "workflows" / "test.yml"

REQUIRED_FRONTMATTER_FIELDS = {
    "name",
    "description",
    "argument-hint",
}

EXPECTED_ACTION_PINS = {
    "actions/checkout": {
        "tag": "v6.0.2",
        "sha": "de0fac2e4500dabe0009e67214ff5f5447ce83dd",
    },
    "actions/setup-python": {
        "tag": "v6.2.0",
        "sha": "a309ff8b426b58ec0e2a45f0f869d46889d02405",
    },
}

LOCAL_REFERENCE_PREFIXES = (
    "agents/",
    "evals/",
    "examples/",
    "references/",
    "scripts/",
    "templates/",
)


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def release_tag() -> str:
    version = read_text(VERSION).strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        fail(f"{VERSION} must contain a semantic version like 0.1.1")
    return f"v{version}"


def frontmatter_fields(text: str) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        fail("SKILL.md is missing YAML frontmatter")

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.startswith(" "):
            continue
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip().strip("\"'")
    return fields


def normalize_skill_reference(raw_reference: str) -> str | None:
    reference = raw_reference.strip()
    reference = reference.removeprefix("${CLAUDE_SKILL_DIR}/")
    reference = reference.removeprefix("$CLAUDE_SKILL_DIR/")
    reference = reference.removeprefix("./")

    for prefix in LOCAL_REFERENCE_PREFIXES:
        if reference.startswith(prefix):
            return reference
    if reference in {"SKILL.md", "LICENSE"}:
        return reference
    return None


def check_skill_frontmatter_and_references() -> None:
    text = read_text(SKILL)
    fields = frontmatter_fields(text)

    missing_fields = sorted(REQUIRED_FRONTMATTER_FIELDS - fields.keys())
    if missing_fields:
        fail(f"SKILL.md frontmatter missing field(s): {', '.join(missing_fields)}")

    if fields["name"] != "hardening-review":
        fail("SKILL.md frontmatter name must be hardening-review")

    # Agent Skills spec limit. Every client reads description, so it must carry the triggers.
    if len(fields["description"]) > 1024:
        fail(
            f"SKILL.md description is {len(fields['description'])} characters; the limit is 1024"
        )
    if "Use when" not in fields["description"]:
        fail("SKILL.md description must say when to use the skill")

    backtick_references = re.findall(r"`([^`]+)`", text)
    markdown_references = re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", text)
    local_references = {
        reference
        for raw in (*backtick_references, *markdown_references)
        if (reference := normalize_skill_reference(raw)) is not None
    }

    missing_paths = sorted(
        reference
        for reference in local_references
        if not (SKILL_DIR / reference).exists()
    )
    if missing_paths:
        fail(f"SKILL.md references missing path(s): {', '.join(missing_paths)}")


def check_readme_release_pins(expected_tag: str) -> None:
    text = read_text(README)
    install_pins = re.findall(r"(?:--branch|checkout)\s+(v\d+\.\d+\.\d+)", text)
    install_pins += re.findall(r"#(v\d+\.\d+\.\d+)", text)
    install_pins += re.findall(r"examples below pin `(v\d+\.\d+\.\d+)`", text)

    if not install_pins:
        fail("README.md must include release-pinned install examples")

    mismatched = sorted({pin for pin in install_pins if pin != expected_tag})
    if mismatched:
        fail(
            "README.md install pins must match "
            f"{expected_tag}; found {', '.join(mismatched)}"
        )


def check_generated_rule_catalog() -> None:
    result = subprocess.run(
        [sys.executable, str(SCANNER), "--list-rules"],
        check=True,
        capture_output=True,
        text=True,
    )
    if read_text(RULES) != result.stdout:
        fail(
            "references/scanner-rules.md is stale; regenerate it with "
            "python3 skills/hardening-review/scripts/fragility_scan.py --list-rules "
            "> skills/hardening-review/references/scanner-rules.md"
        )


def check_claude_skill_dir_scanner_invocation() -> None:
    env = os.environ.copy()
    env["CLAUDE_SKILL_DIR"] = str(SKILL_DIR)
    command = f'"{sys.executable}" "${{CLAUDE_SKILL_DIR}}/scripts/fragility_scan.py" "$PWD" --json'
    result = subprocess.run(
        ["sh", "-c", command],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    scan = json.loads(result.stdout)
    if not isinstance(scan.get("findings"), list):
        fail("scanner JSON from CLAUDE_SKILL_DIR invocation is missing findings")


def check_plugin_manifests(version: str) -> None:
    """plugin.json and marketplace.json carry the released version and point at the skill."""
    plugin = json.loads(read_text(PLUGIN))
    marketplace = json.loads(read_text(MARKETPLACE))
    if plugin.get("name") != "hardening-review":
        fail(f"{PLUGIN} name must be hardening-review")
    if plugin.get("version") != version:
        fail(f"{PLUGIN} version is {plugin.get('version')}; VERSION is {version}")
    entries = [
        e for e in marketplace.get("plugins", []) if e.get("name") == plugin["name"]
    ]
    if len(entries) != 1:
        fail(f"{MARKETPLACE} must list exactly one plugin named {plugin['name']}")
    if entries[0].get("version") != version:
        fail(
            f"{MARKETPLACE} plugin version is {entries[0].get('version')}; VERSION is {version}"
        )
    if entries[0].get("source") != "./":
        fail(f"{MARKETPLACE} plugin source must be ./ (this repository is the plugin)")
    if not (SKILL_DIR / "SKILL.md").is_file():
        fail(f"{SKILL_DIR} must hold SKILL.md so the plugin discovers it under skills/")


def check_github_action_pins() -> None:
    text = read_text(WORKFLOW)
    for action, expected in EXPECTED_ACTION_PINS.items():
        pattern = re.compile(
            rf"uses:\s+{re.escape(action)}@([0-9a-f]{{40}})\s+#\s+({re.escape(expected['tag'])})"
        )
        match = pattern.search(text)
        if not match:
            fail(
                f"{WORKFLOW} must pin {action} to {expected['sha']} "
                f"with comment {expected['tag']}"
            )
        actual_sha, _actual_tag = match.groups()
        if actual_sha != expected["sha"]:
            fail(f"{action} pin is {actual_sha}, expected {expected['sha']}")


def main() -> int:
    expected_tag = release_tag()
    check_plugin_manifests(expected_tag.removeprefix("v"))
    check_skill_frontmatter_and_references()
    check_readme_release_pins(expected_tag)
    check_generated_rule_catalog()
    check_claude_skill_dir_scanner_invocation()
    check_github_action_pins()
    sys.stdout.write("package contract checks passed\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
