import json

import requests

from scoreboard import aggregate, pricing, report
from scoreboard.config import ROOT


def test_summary_written_atomically(job, catalog, tmp_path):
    summary = aggregate.summarize_job(job, catalog)
    out = tmp_path / "summary.json"
    report.write_summary(summary, out)
    assert json.loads(out.read_text())["arms"]["fixed"]["passed"] == 2
    assert not list(tmp_path.glob(".summary-*"))


def test_message_lists_both_arms(job, catalog):
    text = report.format_message(aggregate.summarize_job(job, catalog))
    assert "routed: 50.0% (1/2)" in text
    assert "fixed: 100.0% (2/2)" in text


def test_post_failure_is_logged_not_raised(job, catalog, monkeypatch, caplog):
    def boom(*a, **k):
        raise requests.ConnectionError("chat is down")

    monkeypatch.setattr(requests, "post", boom)
    assert report.post_summary(aggregate.summarize_job(job, catalog), "https://chat.example/hook") is False
    assert "posting summary failed" in caplog.text


def test_catalog_loads():
    catalog = pricing.load_catalog(ROOT / "config" / "prices.toml")
    assert catalog["corvid-7"]["output"] == 15.00
