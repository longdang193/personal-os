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
    def tearDown(self):
        adapter._conversation_locks.clear()

    def test_run_local_reads_async_streams(self):
        class Stream:
            def __init__(self, *values):
                self.values = iter(values)

            async def readline(self):
                return next(self.values, b"")

            async def read(self):
                return b""

        process = SimpleNamespace(
            stdin=SimpleNamespace(write=lambda value: None, drain=AsyncMock(), close=lambda: None),
            stdout=Stream(b"event-1\n", b"event-2\n"),
            stderr=Stream(b""),
            returncode=0,
            wait=AsyncMock(return_value=0),
        )
        on_line = AsyncMock()
        with patch.object(adapter.asyncio, "create_subprocess_exec", new=AsyncMock(return_value=process)):
            result = asyncio.run(adapter._run_local({"request_id": "request-1"}, on_line))

        self.assertEqual(result, (0, ""))
        self.assertEqual([call.args[0] for call in on_line.await_args_list], ["event-1\n", "event-2\n"])

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
        self.assertEqual(envelope["access_mode"], "read")
        self.assertNotIn("secret", envelope)

    def test_envelope_defaults_owner_requests_to_write_mode(self):
        envelope = adapter.build_envelope(
            channel="telegram",
            sender_id="owner",
            chat_id="7",
            content="add to daily plan: need to learn German today",
        )

        self.assertEqual(envelope["access_mode"], "write")

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
        async def run_local(envelope, on_line):
            for line in lines:
                await on_line(line)
            return 0, ""

        with patch.object(adapter, "_run_local", new=run_local), patch.object(adapter, "_send", new=send):
            self.assertTrue(asyncio.run(adapter.handle(SimpleNamespace(), message)))
        rendered = [call.args[2] for call in send.await_args_list]
        self.assertEqual(rendered, ["[accepted] started", "[completed] done"])

        send.reset_mock()
        async def failed_run(envelope, on_line):
            return 1, "runner failed"

        with patch.object(adapter, "_run_local", new=failed_run), patch.object(adapter, "_send", new=send):
            self.assertTrue(asyncio.run(adapter.handle(SimpleNamespace(), message)))
        self.assertIn("runner failed", send.await_args.args[2])

    def test_handle_serializes_same_conversation_but_allows_other_conversations(self):
        started = []
        release_first = asyncio.Event()
        second_started = asyncio.Event()

        def message(chat_id, message_id, content):
            return SimpleNamespace(
                channel="telegram",
                sender_id="owner",
                chat_id=chat_id,
                content=content,
                metadata={"message_id": message_id},
                session_key=f"telegram:{chat_id}",
            )

        async def run_local(envelope, on_line):
            started.append(envelope["request_id"])
            if envelope["request_id"] == "telegram-7-1":
                await release_first.wait()
            else:
                second_started.set()
            return 0, ""

        async def scenario():
            with patch.object(adapter, "_run_local", new=run_local), patch.object(adapter, "_send", new=AsyncMock()):
                first = asyncio.create_task(adapter.handle(SimpleNamespace(), message("7", 1, "first")))
                while not started:
                    await asyncio.sleep(0)
                second = asyncio.create_task(adapter.handle(SimpleNamespace(), message("7", 2, "second")))
                other = asyncio.create_task(adapter.handle(SimpleNamespace(), message("8", 3, "other")))
                await asyncio.wait_for(second_started.wait(), timeout=1)
                self.assertEqual(started, ["telegram-7-1", "telegram-8-3"])
                self.assertFalse(second.done())
                release_first.set()
                await asyncio.gather(first, second, other)

        asyncio.run(scenario())





if __name__ == "__main__":
    unittest.main()
