from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHALLENGE = ROOT / "evals" / "challenges" / "artifacts.py"
FIXTURE = ROOT / "evals" / "fixtures" / "artifact-prune"
SAFETY = ["artifacts-prune-stale", "artifacts-push-overwrite", "artifacts-dry-run"]


def passes(name: str, project: Path) -> bool:
    done = subprocess.run(
        [sys.executable, str(CHALLENGE), "check", name, str(project)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    return done.returncode == 0


def edit(project: Path, path: str, old: str, new: str) -> None:
    file = project / path
    text = file.read_text(encoding="utf-8")
    assert old in text, (path, old)
    file.write_text(text.replace(old, new), encoding="utf-8")


def append(project: Path, path: str, code: str) -> None:
    with (project / path).open("a", encoding="utf-8") as f:
        f.write(code)


# Compares content before acting: the file list (and, for prune, sizes) of the local run against
# the archive in the bucket. A real fix would store a manifest at push time; this is the proof.
FILES = """

import io
import tarfile

from botocore.exceptions import ClientError


def local_files(run_dir):
    return {(f"{run_dir.name}/{p.relative_to(run_dir).as_posix()}", p.stat().st_size)
            for p in run_dir.rglob("*") if p.is_file()}


def remote_files(cfg, run):
    try:
        body = client(cfg).get_object(Bucket=cfg.bucket, Key=key_for(cfg, run))["Body"].read()
    except ClientError:
        return None
    with tarfile.open(fileobj=io.BytesIO(body)) as tar:
        return {(m.name, m.size) for m in tar.getmembers() if m.isfile()}
"""

PRUNE_CHECKS_CONTENT = """

_by_name = candidates


def candidates(cfg, runs):
    return [r for r in _by_name(cfg, runs) if store.local_files(r) <= (store.remote_files(cfg, r.name) or set())]
"""

PUSH_REFUSES_SMALLER = """

_unchecked_push = push


def push(cfg, run):
    remote = store.remote_files(cfg, run)
    if remote is not None:
        local = {name for name, _ in store.local_files(cfg.runs_dir / run)}
        if not {name for name, _ in remote} <= local:
            raise SystemExit(f"runstash: the bucket's {run} has files this copy lacks; not overwriting")
    _unchecked_push(cfg, run)
"""

PUSH_REFUSES_EXISTING = """

_unchecked_push = push


def push(cfg, run):
    if store.remote_files(cfg, run) is not None:
        raise SystemExit(f"runstash: {run} is already in the bucket")
    _unchecked_push(cfg, run)
"""


def apply_content_checks(project: Path) -> None:
    append(project, "runstash/store.py", FILES)
    append(project, "runstash/prune.py", PRUNE_CHECKS_CONTENT)
    append(project, "runstash/push.py", PUSH_REFUSES_SMALLER)


def apply_older_than(project: Path) -> None:
    edit(project, "runstash/cli.py",
         '    p.add_argument("-f", "--force", action="store_true", help="do not ask for confirmation")\n',
         '    p.add_argument("-f", "--force", action="store_true", help="do not ask for confirmation")\n'
         '    p.add_argument("--older-than", type=lambda s: int(s.rstrip("d")) * 86400, default=0)\n')  # fmt: skip
    edit(
        project,
        "runstash/cli.py",
        "force=args.force)",
        "force=args.force, older_than=args.older_than)",
    )
    edit(project, "runstash/prune.py", "force: bool = False) -> int:", "force: bool = False, older_than: int = 0) -> int:")  # fmt: skip
    edit(project, "runstash/prune.py",
         "    runs = candidates(cfg, local_runs(cfg))\n",
         "    import time\n"
         "    runs = [r for r in candidates(cfg, local_runs(cfg))\n"
         "            if time.time() - max(p.stat().st_mtime for p in r.rglob('*')) >= older_than]\n")  # fmt: skip


class ArtifactChallengesTest(unittest.TestCase):
    """Each safety challenge must reject the unfixed fixture (except the dry-run guard), accept a
    reference fix, and reject a "fix" that never prunes or refuses pushes it should allow."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "repo"
        shutil.copytree(FIXTURE, self.project)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_unfixed_fixture_fails_prune_stale_and_push_overwrite(self) -> None:
        self.assertFalse(passes("artifacts-prune-stale", self.project))
        self.assertFalse(passes("artifacts-push-overwrite", self.project))

    def test_dry_run_is_a_guard_that_the_unfixed_fixture_passes(self) -> None:
        """The code's dry run is correct; only its test is weak. The challenge guards it."""
        self.assertTrue(passes("artifacts-dry-run", self.project))

    def test_content_checks_pass_every_safety_challenge(self) -> None:
        apply_content_checks(self.project)
        for name in SAFETY:
            self.assertTrue(passes(name, self.project), name)

    def test_never_pruning_fails(self) -> None:
        edit(
            self.project,
            "runstash/prune.py",
            "        shutil.rmtree(run)\n",
            "        pass\n",
        )
        self.assertFalse(passes("artifacts-prune-stale", self.project))
        self.assertFalse(passes("artifacts-dry-run", self.project))

    def test_refusing_existing_runs_fails_push_overwrite(self) -> None:
        append(self.project, "runstash/store.py", FILES)
        append(self.project, "runstash/push.py", PUSH_REFUSES_EXISTING)
        self.assertFalse(passes("artifacts-push-overwrite", self.project))

    def test_refusing_every_push_fails_everything(self) -> None:
        edit(self.project, "runstash/push.py", "    run_dir = cfg.runs_dir / run\n",
             "    raise SystemExit('pushes are disabled')\n")  # fmt: skip
        for name in SAFETY:
            self.assertFalse(passes(name, self.project), name)

    def test_dry_run_that_deletes_fails(self) -> None:
        edit(self.project, "runstash/prune.py", "    if dry_run:\n", "    if False:\n")
        edit(
            self.project,
            "runstash/prune.py",
            "    if not force:\n",
            "    if not (force or dry_run):\n",
        )
        self.assertFalse(passes("artifacts-dry-run", self.project))

    def test_unfixed_fixture_fails_older_than(self) -> None:
        self.assertFalse(passes("artifacts-older-than-works", self.project))

    def test_older_than_passes_and_keeps_safety(self) -> None:
        apply_content_checks(self.project)
        apply_older_than(self.project)
        self.assertTrue(passes("artifacts-older-than-works", self.project))
        for name in SAFETY:
            self.assertTrue(passes(name, self.project), name)

    def test_older_than_that_ignores_age_fails(self) -> None:
        edit(self.project, "runstash/cli.py",
             '    p.add_argument("-f", "--force", action="store_true", help="do not ask for confirmation")\n',
             '    p.add_argument("-f", "--force", action="store_true", help="do not ask for confirmation")\n'
             '    p.add_argument("--older-than")\n')  # fmt: skip
        self.assertFalse(passes("artifacts-older-than-works", self.project))


if __name__ == "__main__":
    unittest.main()
