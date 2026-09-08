import sys
import unittest
import inspect
from pathlib import Path
from unittest.mock import patch


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

    def test_digest_search_has_bounded_default(self):
        self.assertEqual(inspect.signature(mail.mail_search).parameters["limit"].default, 5)

    def test_empty_account_scope_defaults_to_all(self):
        with patch.object(mail, "_search_one", return_value={"messages": []}) as search:
            result = mail.mail_search("", "", 1)
        self.assertEqual(result["accounts"], ["personal", "student"])
        self.assertEqual(search.call_count, 2)

    def test_himalaya_normalizes_common_gmail_digest_filters(self):
        query = mail._normalize_himalaya_query("in:inbox newer_than:1d")
        self.assertEqual(query, f"after {(mail.date.today() - mail.timedelta(days=1)).isoformat()}")

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

    def test_preserves_himalaya_string_message_body(self):
        self.assertEqual(mail._himalaya_body("Subject: Student\n\nBody"), "Subject: Student\n\nBody")

    def test_extracts_nested_himalaya_body(self):
        self.assertEqual(mail._himalaya_body({"message": {"body": {"text": "Body"}}}), "Body")

    def test_extracts_himalaya_mime_text_part(self):
        self.assertEqual(
            mail._himalaya_body(
                {
                    "text_body": [1],
                    "parts": [
                        {"body": {"Multipart": [1]}},
                        {"body": {"Text": "Body"}},
                    ],
                }
            ),
            "Body",
        )


if __name__ == "__main__":
    unittest.main()
