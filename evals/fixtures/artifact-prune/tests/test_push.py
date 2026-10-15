import io
import tarfile

import pytest

from runstash import config
from runstash.push import push

from .conftest import make_run


def test_push_uploads_run_archive(project, s3):
    make_run(project, "baseline-01", trials=3)
    push(config.load_project(), "baseline-01")
    data = s3.objects[("test-bucket", "exp/baseline-01.tar.gz")]
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        names = tar.getnames()
    assert "baseline-01/run.json" in names
    assert "baseline-01/trials/trial-0003/metrics.json" in names


def test_push_leaves_no_staging_files(project, s3):
    make_run(project, "baseline-01")
    push(config.load_project(), "baseline-01")
    assert list((project / ".runstash" / "staging").iterdir()) == []


def test_push_rejects_a_directory_that_is_not_a_run(project, s3):
    (project / "runs" / "notes").mkdir()
    with pytest.raises(SystemExit):
        push(config.load_project(), "notes")
    assert s3.objects == {}
