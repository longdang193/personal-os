import unittest
from unittest.mock import patch

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import calendar_mcp_server as calendar


class CalendarMcpServerTests(unittest.TestCase):
    def test_search_builds_time_range_request(self):
        with patch.object(calendar, "_gws_call", return_value={"items": []}) as call:
            result = calendar.calendar_search(
                time_min="2026-09-07T00:00:00+02:00",
                time_max="2026-09-08T00:00:00+02:00",
                query="seminar",
                limit=5,
            )

        self.assertEqual(result, {"items": []})
        self.assertEqual(call.call_args.args, ("calendar events list",))
        self.assertEqual(call.call_args.kwargs["params"]["calendarId"], "primary")
        self.assertEqual(call.call_args.kwargs["params"]["timeMin"], "2026-09-07T00:00:00+02:00")
        self.assertEqual(call.call_args.kwargs["params"]["q"], "seminar")

    def test_update_preserves_partial_event_body(self):
        event = {"summary": "New title"}
        with patch.object(calendar, "_gws_call", return_value={"id": "event-1"}) as call:
            result = calendar.calendar_write("update", event_id="event-1", event=event)

        self.assertEqual(result, {"id": "event-1"})
        self.assertEqual(call.call_args.kwargs["body"], event)

    def test_write_rejects_event_without_explicit_time(self):
        with self.assertRaisesRegex(ValueError, "event must contain start and end"):
            calendar.calendar_write("create", event={"summary": "Missing time"})


if __name__ == "__main__":
    unittest.main()
