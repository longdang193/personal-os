import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


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

    def test_normalizes_apify_item_to_social_event(self):
        events = poller.build_apify_events(
            [
                {
                    "id": "post-1",
                    "ownerUsername": "openai",
                    "caption": "New announcement",
                    "url": "https://www.instagram.com/p/post-1/",
                    "timestamp": "2026-09-03T18:00:00Z",
                }
            ],
            "instagram-openai",
            "openai",
            detected_at="2026-09-03T19:00:00Z",
        )

        self.assertEqual(events[0]["event_id"], "instagram-openai:post-1")
        self.assertEqual(events[0]["source_type"], "social")
        self.assertEqual(events[0]["title"], "@openai posted on Instagram")

    def test_load_env_value_reads_quoted_token_without_logging_it(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text('APIFY_TOKEN="secret-value"\n', encoding="utf-8")

            self.assertEqual(poller.load_env_value(env_path, "APIFY_TOKEN"), "secret-value")

    def test_fetch_apify_items_sends_bearer_token_and_json_input(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, _limit):
                return b'[{"id":"post-1"}]'

        with patch.object(poller, "urlopen", return_value=FakeResponse()) as open_url:
            items = poller.fetch_apify_items(["openai"], "2026-09-03T18:50:00Z", "secret", 3, 20)

        request = open_url.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(items, [{"id": "post-1"}])
        self.assertEqual(request.headers["Authorization"], "Bearer secret")
        self.assertEqual(payload["username"], ["openai"])
        self.assertEqual(payload["onlyPostsNewerThan"], "2026-09-03T18:50:00Z")

    def test_fetch_apify_items_requires_token(self):
        with self.assertRaisesRegex(ValueError, "APIFY_TOKEN is required"):
            poller.fetch_apify_items(["openai"], "1 day", "", 1, 20)

    def test_fetch_apify_items_rejects_malformed_response(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, _limit):
                return b'{"items": []}'

        with patch.object(poller, "urlopen", return_value=FakeResponse()):
            with self.assertRaisesRegex(ValueError, "must contain an array"):
                poller.fetch_apify_items(["openai"], "1 day", "secret", 1, 20)


if __name__ == "__main__":
    unittest.main()
