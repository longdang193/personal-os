import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import mail_mcp_server as mail


class MailMcpServerTests(unittest.TestCase):
    def test_validation_keeps_read_boundary(self):
        self.assertEqual(mail._validate_account("all"), "all")
        self.assertEqual(mail._validate_limit(50), 50)
        with self.assertRaises(ValueError):
            mail._validate_account("unknown")
        with self.assertRaises(ValueError):
            mail._validate_account("all", allow_all=False)
        with self.assertRaises(ValueError):
            mail._validate_message_id("..\\secret")
        with self.assertRaises(ValueError):
            mail._validate_limit(0)

    def test_registry_owns_mail_provider_mapping(self):
        self.assertEqual(mail._account_config("personal")["provider"], "google-workspace")
        self.assertEqual(mail._account_config("student")["provider_account"], "ovgu")

    def test_normalizes_gmail_metadata(self):
        result = mail._normalize_gmail(
            {
                "id": "m1",
                "threadId": "t1",
                "labelIds": ["INBOX"],
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Bun Cha"},
                        {"name": "From", "value": "sender@example.test"},
                    ]
                },
                "snippet": "preview",
            },
            include_body=False,
        )
        self.assertEqual(result["id"], "m1")
        self.assertEqual(result["subject"], "Bun Cha")
        self.assertNotIn("body", result)

    def test_normalizes_himalaya_envelope(self):
        result = mail._normalize_himalaya(
            {
                "id": "42",
                "flags": ["Seen"],
                "envelope": {"date": "2026-09-07", "subject": "Student", "from": "sender"},
            }
        )
        self.assertEqual(result["id"], "42")
        self.assertEqual(result["subject"], "Student")
        self.assertEqual(result["flags"], ["Seen"])


if __name__ == "__main__":
    unittest.main()
