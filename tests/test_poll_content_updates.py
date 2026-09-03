import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import poll_content_updates as poller


RSS = b"""<?xml version=\"1.0\"?>
<rss version=\"2.0\"><channel><title>News</title>
<item><guid>news-1</guid><title>Exam registration</title>
<link>https://example.test/news-1</link><description>Register by 15 October.</description>
<pubDate>Thu, 03 Sep 2026 08:00:00 GMT</pubDate></item>
</channel></rss>"""


class PollContentUpdatesTests(unittest.TestCase):
    def test_normalizes_rss_item_to_content_update_event(self):
        items = poller.parse_feed(RSS)
        events = poller.build_events(items, "ovgu-fww-news", "https://example.test/news.rss")

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["schema"], "content.update.v1")
        self.assertEqual(events[0]["event_id"], "ovgu-fww-news:news-1")
        self.assertEqual(events[0]["source_type"], "rss")
        self.assertEqual(events[0]["title"], "Exam registration")
        self.assertEqual(events[0]["item_id"], "news-1")

    def test_state_emits_new_events_once(self):
        events = poller.build_events(
            poller.parse_feed(RSS), "ovgu-fww-news", "https://example.test/news.rss"
        )

        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            state = poller.load_state(state_path)
            first = poller.select_new_events(events, state)
            poller.save_state(state_path, state)
            second = poller.select_new_events(events, poller.load_state(state_path))

        self.assertEqual([event["event_id"] for event in first], ["ovgu-fww-news:news-1"])
        self.assertEqual(second, [])

    def test_rejects_non_http_source_url(self):
        with self.assertRaises(ValueError):
            poller.validate_source_url("file:///private/data.xml")


if __name__ == "__main__":
    unittest.main()
