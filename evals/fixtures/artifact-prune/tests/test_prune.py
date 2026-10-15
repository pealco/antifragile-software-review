import subprocess
import sys

from runstash import config
from runstash.prune import prune
from runstash.push import push

from .conftest import make_run


def test_prune_deletes_pushed_runs(project, s3):
    run = make_run(project, "baseline-01")
    push(config.load_project(), "baseline-01")
    assert prune(config.load(), force=True) == 0
    assert not run.exists()


def test_prune_keeps_runs_that_were_never_pushed(project, s3):
    run = make_run(project, "sweep-lr-3e4")
    prune(config.load(), force=True)
    assert run.exists()


def test_prune_ignores_directories_without_run_json(project, s3):
    judge = project / "runs" / "baseline-01.judge"
    judge.mkdir()
    make_run(project, "baseline-01")
    push(config.load_project(), "baseline-01")
    prune(config.load(), force=True)
    assert judge.exists()


def test_dry_run(project, s3, capsys):
    make_run(project, "baseline-01")
    push(config.load_project(), "baseline-01")
    prune(config.load(), dry_run=True)
    out = capsys.readouterr().out
    assert "would delete baseline-01" in out


def test_force_skips_confirmation(project):
    done = subprocess.run(
        [sys.executable, "-m", "runstash", "prune", "--help"], capture_output=True, text=True, check=True
    )
    assert "--force" in done.stdout


def test_prompt_declined_deletes_nothing(project, s3, monkeypatch):
    run = make_run(project, "baseline-01")
    push(config.load_project(), "baseline-01")
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    assert prune(config.load()) == 1
    assert run.exists()
