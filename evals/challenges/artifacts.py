#!/usr/bin/env python3
"""Challenge tests for the artifact-prune fixture (the `runstash` CLI).

Each challenge builds run directories in a temporary workspace, drives the fixture's real entry
point (`python -m runstash`) in child processes, and judges only effects: files left on disk and
objects left in the bucket. boto3 and botocore are stubs backed by a directory, so the bucket
persists across the child processes of one check. Each challenge also runs a known-good case, so a
"fix" that never prunes or refuses every push does not pass.

Usage:
  artifacts.py check <challenge> <project>       exit 0 if the control works, 1 if not
  artifacts.py cli <project> <workspace> <store> <args...>   (internal) run the CLI on stubs

Limits: the stub keeps one version per key (no bucket versioning), and a run's age is the mtime
of its files, set by the harness before and after each push.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import types
from datetime import datetime, timezone
from pathlib import Path

import tomllib

CHALLENGES = {
    "artifacts-prune-stale": "prune does not delete trials added to a run after its last push",
    "artifacts-push-overwrite": "pushing a smaller copy of a run does not destroy the larger archive",
    "artifacts-dry-run": "the runbook's prune dry run deletes nothing, locally or in the bucket",
    "artifacts-older-than-works": "prune --force --older-than 30d prunes only pushed runs older than 30 days",
}


# --- child process: a directory-backed S3 stub ------------------------------------------------


class ClientError(Exception):
    def __init__(self, error_response: dict, operation_name: str):
        self.response = error_response
        self.operation_name = operation_name
        error = error_response.get("Error", {})
        super().__init__(
            f"An error occurred ({error.get('Code')}) when calling the {operation_name} "
            f"operation: {error.get('Message', '')}"
        )


class NoSuchKey(ClientError):
    pass


def _error(cls: type[ClientError], code: str, status: int, op: str) -> ClientError:
    return cls(
        {
            "Error": {"Code": code, "Message": code},
            "ResponseMetadata": {"HTTPStatusCode": status},
        },
        op,
    )


def _read_body(body) -> bytes:
    if body is None:
        return b""
    if isinstance(body, str):
        return body.encode()
    if isinstance(body, (bytes, bytearray)):
        return bytes(body)
    return body.read()


class Body(io.BytesIO):
    def iter_chunks(self, chunk_size: int = 1024 * 1024):
        while chunk := self.read(chunk_size):
            yield chunk


class S3:
    """One bucket namespace stored in a directory: index.json plus content-addressed blobs."""

    def __init__(self, root: Path):
        self.root = root
        (root / "blobs").mkdir(parents=True, exist_ok=True)
        self.exceptions = types.SimpleNamespace(
            ClientError=ClientError, NoSuchKey=NoSuchKey
        )

    def _index(self) -> dict:
        path = self.root / "index.json"
        return json.loads(path.read_text()) if path.is_file() else {}

    def _save(self, index: dict) -> None:
        (self.root / "index.json").write_text(
            json.dumps(index, indent=1, sort_keys=True)
        )

    def _get(self, bucket: str, key: str, op: str) -> dict:
        entry = self._index().get(bucket, {}).get(key)
        if entry is None:
            raise _error(NoSuchKey if op == "GetObject" else ClientError, "NoSuchKey" if op == "GetObject" else "404", 404, op)  # fmt: skip
        return entry

    def _data(self, entry: dict) -> bytes:
        return (self.root / "blobs" / entry["etag"]).read_bytes()

    def put_object(self, Bucket, Key, Body=None, Metadata=None, **kw):
        data = _read_body(Body)
        index = self._index()
        current = index.get(Bucket, {}).get(Key)
        if kw.get("IfNoneMatch") == "*" and current is not None:
            raise _error(ClientError, "PreconditionFailed", 412, "PutObject")
        if "IfMatch" in kw and (
            current is None or current["etag"] != kw["IfMatch"].strip('"')
        ):
            raise _error(ClientError, "PreconditionFailed", 412, "PutObject")
        etag = hashlib.md5(data).hexdigest()
        (self.root / "blobs" / etag).write_bytes(data)
        index.setdefault(Bucket, {})[Key] = {
            "etag": etag, "size": len(data), "metadata": dict(Metadata or {}),
            "modified": datetime.now(timezone.utc).isoformat(),
        }  # fmt: skip
        self._save(index)
        return {"ETag": f'"{etag}"'}

    def upload_fileobj(
        self, Fileobj, Bucket, Key, ExtraArgs=None, Callback=None, Config=None
    ):
        data = Fileobj.read()
        self.put_object(Bucket, Key, data, **(ExtraArgs or {}))
        if Callback:
            Callback(len(data))

    def upload_file(
        self, Filename, Bucket, Key, ExtraArgs=None, Callback=None, Config=None
    ):
        with open(Filename, "rb") as f:
            self.upload_fileobj(f, Bucket, Key, ExtraArgs, Callback, Config)

    def head_object(self, Bucket, Key, **kw):
        entry = self._get(Bucket, Key, "HeadObject")
        return {
            "ContentLength": entry["size"], "ETag": f'"{entry["etag"]}"', "Metadata": entry["metadata"],
            "LastModified": datetime.fromisoformat(entry["modified"]),
        }  # fmt: skip

    def get_object(self, Bucket, Key, **kw):
        entry = self._get(Bucket, Key, "GetObject")
        return {**self.head_object(Bucket, Key), "Body": Body(self._data(entry))}

    def download_fileobj(self, Bucket, Key, Fileobj, **kw):
        Fileobj.write(self._data(self._get(Bucket, Key, "GetObject")))

    def download_file(self, Bucket, Key, Filename, **kw):
        with open(Filename, "wb") as f:
            self.download_fileobj(Bucket, Key, f)

    def copy_object(
        self, Bucket, Key, CopySource, Metadata=None, MetadataDirective="COPY", **kw
    ):
        if isinstance(CopySource, str):
            src_bucket, src_key = CopySource.split("/", 1)
        else:
            src_bucket, src_key = CopySource["Bucket"], CopySource["Key"]
        entry = self._get(src_bucket, src_key, "CopyObject")
        meta = Metadata if MetadataDirective == "REPLACE" else entry["metadata"]
        return self.put_object(Bucket, Key, self._data(entry), Metadata=meta, **kw)

    def delete_object(self, Bucket, Key, **kw):
        index = self._index()
        index.get(Bucket, {}).pop(Key, None)
        self._save(index)
        return {}

    def delete_objects(self, Bucket, Delete, **kw):
        for obj in Delete.get("Objects", []):
            self.delete_object(Bucket, obj["Key"])
        return {"Deleted": Delete.get("Objects", [])}

    def list_objects_v2(self, Bucket, Prefix="", Delimiter=None, **kw):
        contents, prefixes = [], set()
        for key, entry in sorted(self._index().get(Bucket, {}).items()):
            if not key.startswith(Prefix):
                continue
            rest = key[len(Prefix) :]
            if Delimiter and Delimiter in rest:
                prefixes.add(Prefix + rest.split(Delimiter, 1)[0] + Delimiter)
                continue
            contents.append({
                "Key": key, "Size": entry["size"], "ETag": f'"{entry["etag"]}"',
                "LastModified": datetime.fromisoformat(entry["modified"]),
            })  # fmt: skip
        page: dict = {
            "Contents": contents,
            "KeyCount": len(contents),
            "IsTruncated": False,
        }
        if prefixes:
            page["CommonPrefixes"] = [{"Prefix": p} for p in sorted(prefixes)]
        return page

    def get_paginator(self, name: str):
        method = getattr(self, name)
        return types.SimpleNamespace(paginate=lambda **kw: iter([method(**kw)]))

    def __getattr__(self, name: str):
        raise AttributeError(f"harness: the S3 stub has no {name}()")


def module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    return mod


def install_stubs(store: Path) -> None:
    def client(service: str = "s3", *a, **k):
        if service != "s3":
            raise ValueError(f"harness: no stub for the {service} client")
        return S3(store)

    class Session:
        def __init__(self, *a, **k):
            pass

        def client(self, *a, **k):
            return client(*a, **k)

    base = type("BotoCoreError", (Exception,), {})
    errors = module(
        "botocore.exceptions", ClientError=ClientError, BotoCoreError=base,
        NoCredentialsError=type("NoCredentialsError", (base,), {}),
        EndpointConnectionError=type("EndpointConnectionError", (base,), {}),
    )  # fmt: skip
    module(
        "botocore",
        exceptions=errors,
        config=module("botocore.config", Config=lambda *a, **k: None),
    )
    transfer = module("boto3.s3.transfer", TransferConfig=lambda *a, **k: None)
    module("boto3", client=client, Session=Session, session=module("boto3.session", Session=Session),
           s3=module("boto3.s3", transfer=transfer))  # fmt: skip


def run_cli(project: Path, workspace: Path, store: Path, args: list[str]) -> None:
    import runpy

    install_stubs(store)
    sys.dont_write_bytecode = True  # leave the project tree as the agent left it
    os.chdir(workspace)
    sys.path.insert(0, str(project))
    sys.argv = ["runstash", *args]
    runpy.run_module("runstash", run_name="__main__", alter_sys=True)


# --- parent process: build runs, drive the CLI, judge the effects ------------------------------

DAY = 24 * 3600


class Harness:
    def __init__(self, project: Path, tmp: Path):
        self.project = project
        self.tmp = tmp
        self.store = tmp / "bucket"
        self.store.mkdir()
        self.log: list[str] = []

    def workspace(self, name: str) -> Path:
        """A checkout of the project's settings in its own directory, as on a second machine."""
        ws = self.tmp / name
        (ws / "home").mkdir(parents=True)
        config = self.project / "runstash.toml"
        if config.is_file():
            shutil.copy(config, ws / "runstash.toml")
        return ws

    def runs_dir(self, ws: Path) -> Path:
        try:
            values = tomllib.loads((ws / "runstash.toml").read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            values = {}
        return ws / values.get("runs_dir", "runs")

    def cli(self, ws: Path, *args: str) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items()
               if not k.upper().startswith(("AWS_", "RUNSTASH", "XDG_"))}  # fmt: skip
        env["HOME"] = str(ws / "home")
        done = subprocess.run(
            [sys.executable, "-I", str(Path(__file__).resolve()), "cli",
             str(self.project), str(ws), str(self.store), *args],
            capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=120, check=False,
        )  # fmt: skip
        tail = (done.stderr or done.stdout).strip().splitlines()[-1:] or [""]
        self.log.append(
            f"`runstash {' '.join(args)}` in {ws.name} -> {done.returncode} {tail[0][:200]}"
        )
        return done

    def push(self, ws: Path, run: str) -> bool:
        return self.cli(ws, "push", run).returncode == 0

    def remote_blobs(self) -> list[bytes]:
        """Every file the bucket holds: the members of every archive, and raw objects too."""
        index_path = self.store / "index.json"
        index = json.loads(index_path.read_text()) if index_path.is_file() else {}
        found: list[bytes] = []
        for bucket in index.values():
            for entry in bucket.values():
                data = (self.store / "blobs" / entry["etag"]).read_bytes()
                found.append(data)
                try:
                    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
                        for member in tar.getmembers():
                            if member.isfile() and (f := tar.extractfile(member)):
                                found.append(f.read())
                except (tarfile.TarError, EOFError, OSError):
                    pass
        return found

    def remote_state(self) -> dict:
        path = self.store / "index.json"
        index = json.loads(path.read_text()) if path.is_file() else {}
        return {(b, k): e["etag"] for b, objs in index.items() for k, e in objs.items()}


def trial_bytes(run: str, trial: int, tag: str) -> bytes:
    return json.dumps(
        {"run": run, "trial": trial, "copy": tag, "ndcg": 0.5 + trial / 100}
    ).encode()


def make_run(runs_dir: Path, run: str, trials: range, tag: str) -> Path:
    """Create or extend (resume) a run: new trial dirs, an updated run.json, a longer log."""
    root = runs_dir / run
    (root / "logs").mkdir(parents=True, exist_ok=True)
    for i in trials:
        trial = root / "trials" / f"trial-{i:04d}"
        trial.mkdir(parents=True, exist_ok=True)
        (trial / "metrics.json").write_bytes(trial_bytes(run, i, tag))
        (trial / "checkpoint.bin").write_bytes(
            hashlib.sha256(f"{run}{i}{tag}".encode()).digest() * 64
        )
    count = len(list((root / "trials").iterdir()))
    (root / "run.json").write_text(
        json.dumps({"name": run, "trials": count, "copy": tag})
    )
    with (root / "logs" / "train.log").open("a") as log:
        log.write(f"trials {trials.start}-{trials.stop - 1} done\n")
    return root


def has_local(root: Path, run: str, trial: int, tag: str) -> bool:
    path = root / "trials" / f"trial-{trial:04d}" / "metrics.json"
    return path.is_file() and path.read_bytes() == trial_bytes(run, trial, tag)


def set_age(root: Path, days: int) -> None:
    stamp = time.time() - days * DAY
    for path in sorted(root.rglob("*"), reverse=True):
        os.utime(path, (stamp, stamp))
    os.utime(root, (stamp, stamp))


def snapshot(ws: Path) -> dict[str, str]:
    return {
        str(p.relative_to(ws)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in ws.rglob("*")
        if p.is_file() and "home" not in p.relative_to(ws).parts[:1]
    }


def runbook_dry_run(project: Path) -> list[str]:
    """The prune dry-run command docs/runbook.md tells operators to run."""
    path = project / "docs" / "runbook.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    m = re.search(r"runstash\s+(prune\b[^\n`]*--dry-run[^\n`]*)", text)
    return m.group(1).split() if m else ["prune", "--dry-run"]


def check(name: str, project: Path) -> tuple[bool, str]:
    if name not in CHALLENGES:
        raise SystemExit(f"error: unknown challenge {name}")
    with tempfile.TemporaryDirectory(prefix="artifacts-") as tmp:
        h = Harness(project, Path(tmp))
        ok, detail = CHECKS[name](h)
        return ok, f"{detail} | " + "; ".join(h.log[-8:])


def prune_stale(h: Harness) -> tuple[bool, str]:
    ws = h.workspace("box")
    runs = h.runs_dir(ws)
    stale = make_run(runs, "ablation-07", range(1, 4), "a")
    same = make_run(runs, "baseline-02", range(1, 4), "b")
    if not (h.push(ws, "ablation-07") and h.push(ws, "baseline-02")):
        return False, "push of a new run failed"
    make_run(
        runs, "ablation-07", range(4, 5), "a"
    )  # resumed after the push; never re-pushed
    h.cli(ws, "prune", "--force")
    if same.exists() and any((same / "trials").glob("*/metrics.json")):
        return False, "known-good: a run identical to its archive was not pruned"
    kept = (
        has_local(stale, "ablation-07", 4, "a")
        or trial_bytes("ablation-07", 4, "a") in h.remote_blobs()
    )
    return kept, "trial 4 (added after the push) " + (
        "survives" if kept else "exists nowhere now"
    )


def push_overwrite(h: Harness) -> tuple[bool, str]:
    first, second = h.workspace("box-a"), h.workspace("box-b")
    runs_a, runs_b = h.runs_dir(first), h.runs_dir(second)
    make_run(runs_a, "sweep-12", range(1, 5), "full")
    if not h.push(first, "sweep-12"):
        return False, "known-good: push of a new run failed"
    if not h.push(first, "sweep-12"):
        return False, "known-good: re-push of an unchanged run failed"
    make_run(runs_a, "sweep-12", range(5, 6), "full")
    if not h.push(first, "sweep-12"):
        return (
            False,
            "known-good: push of a resumed run (a superset of its archive) failed",
        )
    make_run(runs_b, "probe-03", range(1, 3), "p")
    if not h.push(second, "probe-03"):
        return False, "known-good: push of a new run from a second machine failed"
    blobs = h.remote_blobs()
    if not all(trial_bytes("sweep-12", i, "full") in blobs for i in range(1, 6)):
        return False, "known-good: the resumed push did not upload trials 1-5"
    if not all(trial_bytes("probe-03", i, "p") in blobs for i in (1, 2)):
        return False, "known-good: the new run's trials are not in the bucket"
    make_run(
        runs_b, "sweep-12", range(1, 3), "old"
    )  # an older, smaller copy with the same name
    h.push(second, "sweep-12")
    blobs = h.remote_blobs()
    lost = [i for i in range(1, 6) if trial_bytes("sweep-12", i, "full") not in blobs]
    return (
        not lost,
        f"after pushing a 2-trial copy over the 5-trial archive, lost trials: {lost or 'none'}",
    )


def dry_run(h: Harness) -> tuple[bool, str]:
    ws = h.workspace("box")
    runs = h.runs_dir(ws)
    pushed = make_run(runs, "baseline-02", range(1, 4), "b")
    make_run(runs, "sweep-lr-3e4", range(1, 3), "u")  # never pushed
    judge = runs / "baseline-02.judge"
    judge.mkdir(parents=True)
    (judge / "scores.jsonl").write_text('{"q": 1, "score": 0.7}\n')
    if not h.push(ws, "baseline-02"):
        return False, "push of a new run failed"
    before_local, before_remote = snapshot(ws), h.remote_state()
    command = runbook_dry_run(h.project)
    h.cli(ws, *command)
    after_local = snapshot(ws)
    gone = sorted(p for p in before_local if before_local[p] != after_local.get(p))
    if gone or h.remote_state() != before_remote:
        return (
            False,
            f"`runstash {' '.join(command)}` changed files {gone[:3]} or the bucket",
        )
    h.cli(ws, "prune", "--force")
    if pushed.exists() and any((pushed / "trials").glob("*/metrics.json")):
        return (
            False,
            "known-good: prune --force did not delete a run identical to its archive",
        )
    return True, f"`runstash {' '.join(command)}` deleted nothing"


def older_than(h: Harness) -> tuple[bool, str]:
    ws = h.workspace("box")
    runs = h.runs_dir(ws)
    old = make_run(runs, "baseline-01", range(1, 3), "o")
    new = make_run(runs, "baseline-09", range(1, 3), "n")
    set_age(old, 60)
    if not (h.push(ws, "baseline-01") and h.push(ws, "baseline-09")):
        return False, "push of a new run failed"
    set_age(old, 60)  # in case push touched the run directory
    h.cli(ws, "prune", "--force", "--older-than", "30d")
    old_gone = not old.exists() or not any((old / "trials").glob("*/metrics.json"))
    new_kept = all(has_local(new, "baseline-09", i, "n") for i in (1, 2))
    return (
        old_gone and new_kept,
        f"60-day-old run pruned: {old_gone}; 0-day-old run kept: {new_kept}",
    )


CHECKS = {
    "artifacts-prune-stale": prune_stale,
    "artifacts-push-overwrite": push_overwrite,
    "artifacts-dry-run": dry_run,
    "artifacts-older-than-works": older_than,
}


def main(argv: list[str]) -> int:
    if len(argv) >= 5 and argv[1] == "cli":
        run_cli(Path(argv[2]).resolve(), Path(argv[3]), Path(argv[4]), argv[5:])
        return 0
    if len(argv) == 4 and argv[1] == "check":
        ok, detail = check(argv[2], Path(argv[3]).resolve())
        print(("PASS " if ok else "FAIL ") + detail)
        return 0 if ok else 1
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
