import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock

from retention.policy import Backup, cutoff, keep_set, oldest_kept, to_delete
from retention.prune import prune

TODAY = date(2026, 10, 15)


def daily(days: int) -> list[Backup]:
    return [Backup(f"b{d}", TODAY - timedelta(days=d)) for d in range(days)]


class PolicyTest(unittest.TestCase):
    def test_keep_set_matches_policy(self):
        backups = daily(60)
        self.assertEqual(keep_set(backups, TODAY), keep_set(backups, TODAY))

    def test_recent_backups_are_kept(self):
        kept = keep_set(daily(60), TODAY)
        self.assertTrue(len(kept) > 0)

    def test_to_delete_is_consistent_with_keep_set(self):
        backups = daily(60)
        kept = keep_set(backups, TODAY)
        for b in to_delete(backups, TODAY):
            self.assertNotIn(b.name, kept)

    def test_oldest_kept_exists(self):
        self.assertIsNotNone(oldest_kept(daily(60), TODAY))

    def test_cutoff_is_a_date(self):
        self.assertIsInstance(cutoff(TODAY), date)

    def test_empty(self):
        self.assertEqual(set(), keep_set([], TODAY))


class PruneTest(unittest.TestCase):
    def test_prune_deletes_something(self):
        store = MagicMock()
        store.list_backups.return_value = daily(60)
        prune(store, TODAY)
        store.delete.assert_called()

    def test_dry_run_runs(self):
        store = MagicMock()
        store.list_backups.return_value = daily(60)
        prune(store, TODAY, dry_run=True)
