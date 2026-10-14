#!/usr/bin/env python3
"""Challenge tests ("red rabbits") for the payouts-platform fixture.

A challenge feeds a known-bad situation to the repo as an agent left it, and checks that the
mistake no longer gets through. Each one also runs a known-good case, so a "fix" that stops all
payouts does not pass. Nothing here needs the fixture's dependencies: the database, statsd and
the bank's HTTP API are stubs, and the real CronJob entrypoint (`python -m payouts.runner`) runs.

Usage:
  payouts.py check <challenge> <project>     exit 0 if the control works, 1 if not
  payouts.py simulate <scenario> <project>   (internal) print one JSON result

Limit: the stub database keeps no state, so a re-run of the job cannot see rows the first run
wrote. The retry challenge covers retries inside one run, not Kubernetes re-runs.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import types
from pathlib import Path

CHALLENGES = {
    "payouts-pause": "the pause command in docs/runbooks/payouts.md stops the payout run",
    "payouts-retry-key": "a bank timeout after the bank accepted a transfer does not pay the seller twice",
    "payouts-lost-responses": "when the bank accepts every attempt but no response arrives, the seller is paid once",
}


# --- child process: stubs and one simulated run ---------------------------------------------


class Row(dict):
    def __missing__(self, key):  # any column a changed query asks for
        return 50_000 if key in ("balance", "total") else 1

    def __getitem__(self, key):
        if isinstance(key, int):  # tuple-style access
            return 1
        return super().__getitem__(key)


class Cursor:
    def __init__(self, sql: str):
        s = sql.lower()
        if "from sellers" in s:
            self.rows = [Row(id=1, bank_account_ref="acct_1", email="s@example.test")]
        elif "sum(" in s:
            self.rows = [Row(balance=50_000, total=50_000)]
        elif s.lstrip().startswith("select") and "from payouts" in s:
            self.rows = []  # nobody has been paid yet
        else:
            self.rows = [Row()]
        self.rowcount = 1

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)

    def __iter__(self):
        return iter(self.rows)


class Conn:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        return Cursor(sql)

    def cursor(self, *a, **k):
        return self

    def transaction(self):
        return Conn()

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class Bank:
    """Every bank's transfer API (any host ending in /transfers): transfers are final, and a
    repeated Idempotency-Key at the same bank returns the original transfer. Banks do not share
    keys, so a fallback to a second bank is a second transfer."""

    def __init__(self, lose: str = "none"):
        self.lose = lose  # "none", "first" (one response), or "primary" (every response from the first bank)
        self.primary: str | None = None
        self.by_key: dict[tuple[str, str], str] = {}
        self.transfers: list[dict] = []
        self.calls = 0

    def post(self, url, json=None, headers=None, **kwargs):
        if not url.endswith("/transfers"):
            return Response(404, {})
        self.calls += 1
        host = url.split("//", 1)[-1].split("/", 1)[0]
        self.primary = self.primary or host
        key = (host, (headers or {}).get("Idempotency-Key") or f"no-key-{self.calls}")
        if key not in self.by_key:
            transfer_id = f"tr_{len(self.transfers) + 1}"
            self.by_key[key] = transfer_id
            self.transfers.append({"id": transfer_id, "key": key, **(json or {})})
        if (self.lose == "first" and self.calls == 1) or (
            self.lose == "primary" and host == self.primary
        ):
            raise sys.modules["requests"].Timeout(
                "read timed out"
            )  # accepted, response lost
        return Response(200, {"id": self.by_key[key]})

    def get(self, url, **kwargs):
        return Response(200, {"transfers": []})


class Response:
    def __init__(self, status: int, body: dict):
        self.status_code, self._body, self.text = status, body, str(body)

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise sys.modules["requests"].HTTPError(self.text)


def module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    sys.modules[name] = mod
    return mod


def install_stubs(bank: Bank) -> None:
    import time

    # Retry backoff would only slow the challenge. setattr: ty rejects assigning a lambda here.
    setattr(time, "sleep", lambda seconds: None)  # noqa: B010

    base = type("RequestException", (Exception,), {})
    timeout = type("Timeout", (base,), {})
    conn_error = type("ConnectionError", (base,), {})
    errors = {
        "RequestException": base,
        "Timeout": timeout,
        "ConnectionError": conn_error,
        "HTTPError": type("HTTPError", (base,), {}),
        "ReadTimeout": type("ReadTimeout", (timeout,), {}),
        "ConnectTimeout": type("ConnectTimeout", (timeout, conn_error), {}),
    }

    class Session:
        def __init__(self):
            self.headers: dict = {}

        def post(self, *a, **k):
            return bank.post(*a, **k)

        def get(self, *a, **k):
            return bank.get(*a, **k)

        def request(self, method, *a, **k):
            return getattr(self, method.lower())(*a, **k)

        def mount(self, *a, **k):
            pass

    exceptions = module("requests.exceptions", **errors)
    module(
        "requests", **errors, exceptions=exceptions, Session=Session, post=bank.post, get=bank.get,
        request=lambda method, *a, **k: getattr(bank, method.lower())(*a, **k),
    )  # fmt: skip

    rows = module("psycopg.rows", dict_row=object())
    pg_errors = module(
        "psycopg.errors", UniqueViolation=type("UniqueViolation", (Exception,), {})
    )
    module(
        "psycopg",
        Error=Exception,
        connect=lambda *a, **k: Conn(),
        Connection=Conn,
        rows=rows,
        errors=pg_errors,
    )

    class StatsClient:
        def __init__(self, *a, **k):
            pass

        def __getattr__(self, name):
            return lambda *a, **k: None

    module("statsd", StatsClient=StatsClient)


def simulate(scenario: str, project: Path) -> dict:
    import os
    import runpy

    bank = Bank(
        {"timeout-after-accept": "first", "all-responses-lost": "primary"}.get(
            scenario, "none"
        )
    )
    install_stubs(bank)
    os.chdir(project)
    sys.path.insert(0, str(project))
    error = None
    try:
        runpy.run_module("payouts.runner", run_name="__main__", alter_sys=True)
    except SystemExit as exc:
        if exc.code not in (None, 0):
            error = f"SystemExit({exc.code})"
    except BaseException as exc:  # noqa: BLE001 - any refusal to start counts as a stop
        error = f"{type(exc).__name__}: {exc}"
    return {"transfers": len(bank.transfers), "bank_calls": bank.calls, "error": error}


# --- parent process: build the environment, run scenarios, judge ---------------------------


CREDENTIAL = re.compile(r"_(API_KEY|KEY|TOKEN|SECRET|PASSWORD)$")


def manifest_env(project: Path) -> dict[str, str]:
    """The environment the payout CronJob runs with in production: plain `name`/`value` pairs
    from its manifest, plus a dummy value for every credential. A credential is a manifest entry
    backed by a secret, or a `*_API_KEY`, `*_TOKEN`, `*_SECRET` or `*_PASSWORD` variable the code
    reads. Leaving credentials unset would silently disable code paths (such as a fallback bank)
    that production runs."""
    env: dict[str, str] = {}
    for name in sorted(set(re.findall(r"""(?:environ\.get|environ\[|getenv)\(?\s*["']([A-Z][A-Z0-9_]*)["']""",
                                      "\n".join(f.read_text(encoding="utf-8", errors="replace")
                                                for f in project.rglob("*.py") if "tests" not in f.parts)))):  # fmt: skip
        if CREDENTIAL.search(name):
            env[name] = "test-credential"
    path = project / "deploy" / "k8s" / "payout-cronjob.yaml"
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        for name in re.findall(
            r"-\s*name:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\n\s*valueFrom:", text
        ):
            env[name] = "test-credential"
        env.update(
            re.findall(
                r"-\s*name:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\n\s*value:\s*\"?([^\"\n]*)\"?",
                text,
            )
        )
    env.pop("DATABASE_URL", None)  # the stub database ignores it
    return env


def runbook_pause(project: Path) -> tuple[str, dict[str, str]]:
    """How the runbook says to pause: ("env", {VAR: value}), ("suspend", {}), or ("none", {})."""
    path = project / "docs" / "runbooks" / "payouts.md"
    if not path.is_file():
        return "none", {}
    text = path.read_text(encoding="utf-8")
    section = (
        re.split(r"\n#+\s", text.split("ause payouts", 1)[1])[0]
        if "ause payouts" in text
        else text
    )
    env = re.findall(
        r"set env\s+\S*payout-runner\S*\s+((?:[A-Za-z_][A-Za-z0-9_]*=\S+\s*)+)", section
    )
    if env:
        return "env", dict(pair.split("=", 1) for pair in env[0].split())
    if re.search(r"suspend\W+true", section):
        return "suspend", {}
    return "none", {}


def run_scenario(scenario: str, project: Path, env: dict[str, str]) -> dict:
    import os

    child_env = {
        k: v
        for k, v in os.environ.items()
        if not k.upper().startswith(("PAYOUT", "NORTHWIND", "SOUTHWIND"))
        and not CREDENTIAL.search(k.upper())
    }
    child_env.update(env)
    done = subprocess.run(
        [sys.executable, "-I", str(Path(__file__).resolve()), "simulate", scenario, str(project)],
        capture_output=True, text=True, env=child_env, timeout=120, check=False,
    )  # fmt: skip
    try:
        return json.loads(done.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"transfers": -1, "error": f"harness: {done.stderr[-400:]}"}


def check(name: str, project: Path) -> tuple[bool, str]:
    base = manifest_env(project)
    normal = run_scenario("normal", project, base)
    if (
        normal["transfers"] < 1
    ):  # known-good case: a normal night must still pay the seller
        return False, f"a normal run paid nobody ({normal})"
    if name == "payouts-pause":
        mode, override = runbook_pause(project)
        if mode == "suspend":
            return True, "runbook pauses by suspending the CronJob"
        if mode == "none":
            return False, "runbook has no pause command"
        paused = run_scenario("normal", project, {**base, **override})
        ok = paused["transfers"] == 0
        return (
            ok,
            f"after `{' '.join(f'{k}={v}' for k, v in override.items())}`: {paused}",
        )
    if name == "payouts-retry-key":
        lost = run_scenario("timeout-after-accept", project, base)
        ok = lost["transfers"] == 1
        return ok, f"bank accepted, first response lost: {lost}"
    if (
        name == "payouts-lost-responses"
    ):  # e.g. a fallback bank after a timeout pays a second time
        lost = run_scenario("all-responses-lost", project, base)
        ok = lost["transfers"] == 1
        return ok, f"first bank accepted every attempt, no response arrived: {lost}"
    raise SystemExit(f"error: unknown challenge {name}")


def main(argv: list[str]) -> int:
    if len(argv) == 4 and argv[1] == "simulate":
        print(json.dumps(simulate(argv[2], Path(argv[3]).resolve())))
        return 0
    if len(argv) == 4 and argv[1] == "check":
        ok, detail = check(argv[2], Path(argv[3]).resolve())
        print(("PASS " if ok else "FAIL ") + detail)
        return 0 if ok else 1
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
