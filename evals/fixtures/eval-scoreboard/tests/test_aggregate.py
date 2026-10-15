import pytest

from scoreboard import aggregate


def test_pass_rate_per_arm(job, catalog):
    summary = aggregate.summarize_job(job, catalog)
    assert summary["arms"]["routed"]["pass_rate"] == 0.5
    assert summary["arms"]["fixed"]["pass_rate"] == 1.0


def test_every_trial_is_counted(job, catalog):
    summary = aggregate.summarize_job(job, catalog)
    assert summary["arms"]["routed"]["trials"] == 2
    assert summary["arms"]["fixed"]["trials"] == 2


def test_tokens_are_summed(job, catalog):
    summary = aggregate.summarize_job(job, catalog)
    assert summary["arms"]["fixed"]["input_tokens"] == 20_000
    assert summary["arms"]["fixed"]["output_tokens"] == 2_000


def test_cost_uses_catalog_prices(job, catalog):
    summary = aggregate.summarize_job(job, catalog)
    # 2 trials x (10k in x $3 + 1k out x $15) per million tokens
    assert summary["arms"]["fixed"]["cost_usd"] == pytest.approx(0.09)


def test_routed_calls_counted(job, catalog):
    summary = aggregate.summarize_job(job, catalog)
    assert summary["arms"]["routed"]["routed_calls"] == 2
    assert summary["arms"]["fixed"]["routed_calls"] == 0
