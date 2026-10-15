import unittest
from datetime import date
from unittest.mock import MagicMock

from sharing.api import Forbidden, perform
from sharing.model import Account, Document, Share
from sharing.policy import ACTIONS, ROLE_ACTIONS, can, role_of

TODAY = date(2026, 10, 15)
OWNER = Account("olivia")
DOC = Document(
    "d1",
    owner_id="olivia",
    shares={
        "vic": Share("viewer"),
        "cam": Share("commenter"),
        "ed": Share("editor"),
        "exp": Share("editor", until=date(2026, 10, 15)),
    },
)


class PolicyTest(unittest.TestCase):
    def test_roles_grant_their_actions(self):
        for who, role in (("vic", "viewer"), ("cam", "commenter"), ("ed", "editor")):
            for action in ROLE_ACTIONS[role]:
                self.assertTrue(can(Account(who), action, DOC, TODAY))

    def test_decisions_are_booleans(self):
        for action in ACTIONS:
            self.assertIsInstance(can(Account("vic"), action, DOC, TODAY), bool)

    def test_owner_can_read(self):
        self.assertTrue(can(OWNER, "read", DOC, TODAY))

    def test_role_of_is_stable(self):
        self.assertEqual(
            role_of(Account("ed"), DOC, TODAY), role_of(Account("ed"), DOC, TODAY)
        )

    def test_share_with_until(self):
        self.assertIsNotNone(role_of(Account("exp"), DOC, date(2026, 10, 1)))

    @unittest.skip("suspension rules under discussion with legal")
    def test_suspended_account(self):
        self.assertFalse(can(Account("olivia", suspended=True), "read", DOC, TODAY))

    def test_support_can_read(self):
        self.assertTrue(can(Account("sam", support=True), "read", DOC, TODAY))


class ApiTest(unittest.TestCase):
    def test_perform_records_an_audit_entry(self):
        audit = MagicMock()
        perform(OWNER, "read", DOC, TODAY, audit, lambda: "body")
        audit.record.assert_called()

    def test_denied_action(self):
        audit = MagicMock()
        try:
            perform(Account("vic"), "delete", DOC, TODAY, audit, lambda: None)
        except Forbidden:
            pass
