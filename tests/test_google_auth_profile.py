import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "read_google_auth_profile.py"
sys.path.insert(0, str(ROOT / "scripts"))
import read_google_auth_profile as helper


class GoogleAuthProfileTests(unittest.TestCase):
    def test_helper_returns_exact_redacted_profile(self):
        result = subprocess.run([sys.executable, str(HELPER)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload), {"ok", "profile"})
        self.assertNotIn("redact_output", payload["profile"])
        self.assertEqual(payload["profile"]["provider"], "google-workspace")
        self.assertEqual(payload["profile"]["scopes"], [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar",
        ])

    def test_helper_rejects_invalid_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tool_registry.toml"
            path.write_text("version = 1\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                helper.load_profile(path)

    def test_helper_cli_error_envelopes(self):
        for error, expected_code, expected_output in (
            (ValueError, 2, '{"ok":false,"error":"invalid_profile"}\n'),
            (OSError, 3, '{"ok":false,"error":"profile_unavailable"}\n'),
        ):
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr), patch.object(helper, "load_profile", side_effect=error):
                self.assertEqual(helper.main(), expected_code)
            self.assertEqual(stdout.getvalue(), expected_output)
            self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
