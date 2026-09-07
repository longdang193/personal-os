import asyncio
import json
import unittest
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import personal_edge_adapter as adapter


class PersonalEdgeAdapterTests(unittest.TestCase):
    def test_run_local_reads_async_streams(self):
        class Stream:
            def __init__(self, value):
                self.value = value

            async def read(self):
                return self.value

        process = SimpleNamespace(
            stdin=SimpleNamespace(write=lambda value: None, drain=AsyncMock(), close=lambda: None),
            stdout=Stream(b"event-1\nevent-2\n"),
            stderr=Stream(b""),
            returncode=0,
            wait=AsyncMock(return_value=0),
        )
        with patch.object(adapter.asyncio, "create_subprocess_exec", new=AsyncMock(return_value=process)):
            result = asyncio.run(adapter._run_local({"request_id": "request-1"}))

        self.assertEqual(result, (0, ["event-1\n", "event-2\n"], ""))

    def test_envelope_is_stable_and_forwards_only_repository_metadata(self):
        metadata = {
            "message_id": 42,
            "repository_id": "personal-os",
            "repository_ref": "master",
            "access_mode": "read",
            "secret": "must-not-forward",
        }
        envelope = adapter.build_envelope(
            channel="telegram",
            sender_id="owner",
            chat_id="7",
            content="/status",
            metadata=metadata,
            session_key="telegram:7",
        )
        self.assertEqual(envelope["request_id"], "telegram-7-42")
        self.assertTrue(envelope["command"])
        self.assertEqual(envelope["repository_id"], "personal-os")
        self.assertNotIn("secret", envelope)

    def test_event_validation_preserves_request_identity(self):
        event = {
            "version": "personal.event.v1",
            "request_id": "telegram-7-42",
            "sequence": 0,
            "type": "accepted",
            "payload": {"text": "accepted"},
        }
        self.assertEqual(adapter.validate_event(event, "telegram-7-42"), event)
        with self.assertRaises(ValueError):
            adapter.validate_event({**event, "request_id": "other"}, "telegram-7-42")

    def test_handle_renders_local_jsonl_and_runner_failure(self):
        message = SimpleNamespace(
            channel="telegram",
            sender_id="owner",
            chat_id="7",
            content="hello",
            metadata={"message_id": 42},
            session_key="telegram:7",
        )
        lines = [
            json.dumps({
                "version": "personal.event.v1",
                "request_id": "telegram-7-42",
                "sequence": 0,
                "type": "accepted",
                "payload": {"text": "started"},
            }),
            json.dumps({
                "version": "personal.event.v1",
                "request_id": "telegram-7-42",
                "sequence": 1,
                "type": "completed",
                "payload": {"text": "done"},
            }),
        ]
        send = AsyncMock()
        with patch.object(adapter, "_run_local", new=AsyncMock(return_value=(0, lines, ""))), patch.object(adapter, "_send", new=send):
            self.assertTrue(asyncio.run(adapter.handle(SimpleNamespace(), message)))
        rendered = [call.args[2] for call in send.await_args_list]
        self.assertEqual(rendered, ["[accepted] started", "[completed] done"])

        send.reset_mock()
        with patch.object(adapter, "_run_local", new=AsyncMock(return_value=(1, [], "runner failed"))), patch.object(adapter, "_send", new=send):
            self.assertTrue(asyncio.run(adapter.handle(SimpleNamespace(), message)))
        self.assertIn("runner failed", send.await_args.args[2])





if __name__ == "__main__":
    unittest.main()
