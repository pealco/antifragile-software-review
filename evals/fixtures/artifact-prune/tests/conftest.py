import json
from pathlib import Path

import pytest

from runstash import store


class FakeS3:
    """The parts of the S3 client runstash uses, in memory."""

    def __init__(self):
        self.objects: dict[tuple[str, str], bytes] = {}

    def upload_file(self, filename, bucket, key, ExtraArgs=None, Config=None, Callback=None):
        data = Path(filename).read_bytes()
        self.objects[(bucket, key)] = data
        if Callback:
            Callback(len(data))

    def head_object(self, Bucket, Key):
        return {"ContentLength": len(self.objects[(Bucket, Key)])}

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return self

    def paginate(self, Bucket, Prefix=""):
        yield {
            "Contents": [
                {"Key": key, "Size": len(data)}
                for (bucket, key), data in sorted(self.objects.items())
                if bucket == Bucket and key.startswith(Prefix)
            ]
        }


@pytest.fixture()
def s3(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(store, "client", lambda cfg: fake)
    return fake


@pytest.fixture()
def project(tmp_path, monkeypatch):
    (tmp_path / "runstash.toml").write_text('bucket = "test-bucket"\nprefix = "exp"\nruns_dir = "runs"\n')
    (tmp_path / "runs").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return tmp_path


def make_run(project: Path, name: str, trials: int = 2) -> Path:
    run = project / "runs" / name
    (run / "logs").mkdir(parents=True)
    (run / "run.json").write_text(json.dumps({"name": name, "trials": trials}))
    (run / "logs" / "train.log").write_text("step 1 loss 0.9\n")
    for i in range(1, trials + 1):
        trial = run / "trials" / f"trial-{i:04d}"
        trial.mkdir(parents=True)
        (trial / "metrics.json").write_text(json.dumps({"trial": i, "ndcg": 0.5 + i / 100}))
    return run
