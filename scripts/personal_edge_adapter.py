"""Forward Nanobot edge messages to Personal CoS."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path


EVENT_TYPES = {
    "accepted",
    "progress",
    "question",
    "approval_required",
    "completed",
    "failed",
    "cancelled",
}
FORWARDED_METADATA = ("repository_id", "repository_ref", "access_mode")
DEFAULT_ACCESS_MODE = "write"


def request_id(*, channel: str, sender_id: str, chat_id: str, content: str, metadata: Mapping | None) -> str:
    message_id = (metadata or {}).get("message_id")
    if message_id is not None:
        return f"telegram-{chat_id}-{message_id}"
    raw = "\0".join((channel, sender_id, chat_id, content))
    return f"edge-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def build_envelope(
    *,
    channel: str,
    sender_id: str,
    chat_id: str,
    content: str,
    metadata: Mapping | None = None,
    session_key: str | None = None,
) -> dict:
    metadata = metadata or {}
    envelope = {
        "version": "personal.edge.v1",
        "request_id": request_id(
            channel=channel,
            sender_id=sender_id,
            chat_id=chat_id,
            content=content,
            metadata=metadata,
        ),
        "conversation_id": session_key or f"{channel}:{chat_id}",
        "principal": {"channel": channel, "id": sender_id},
        "text": content,
        "command": content.startswith("/"),
    }
    for key in FORWARDED_METADATA:
        if key in metadata:
            envelope[key] = metadata[key]
    envelope.setdefault("access_mode", DEFAULT_ACCESS_MODE)
    return envelope


def validate_event(event: object, expected_request_id: str) -> dict:
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    if event.get("version") != "personal.event.v1":
        raise ValueError("unsupported event version")
    if event.get("request_id") != expected_request_id:
        raise ValueError("event request_id does not match request")
    if not isinstance(event.get("sequence"), int) or event["sequence"] < 0:
        raise ValueError("event sequence must be a non-negative integer")
    if event.get("type") not in EVENT_TYPES:
        raise ValueError("unsupported event type")
    if not isinstance(event.get("payload"), dict):
        raise ValueError("event payload must be an object")
    return event


def render_event(event: Mapping) -> str:
    payload = event["payload"]
    text = payload.get("text", payload.get("message"))
    if not isinstance(text, str):
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return f"[{event['type']}] {text}"


async def _run_local(envelope: dict, on_line) -> tuple[int, str]:
    launcher = Path(__file__).with_name("personal_cos_launcher.py")
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(launcher),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        assert process.stdin is not None
        process.stdin.write(json.dumps(envelope, ensure_ascii=False).encode("utf-8"))
        await process.stdin.drain()
        process.stdin.close()
        stderr_task = asyncio.create_task(process.stderr.read())
        try:
            while line := await process.stdout.readline():
                await on_line(line.decode("utf-8", errors="replace"))
            stderr = (await stderr_task).decode("utf-8")
            return await process.wait(), stderr
        finally:
            if not stderr_task.done():
                stderr_task.cancel()
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


async def _send(channel, message, content: str) -> None:
    from nanobot.bus.events import OutboundMessage

    await channel.send(
        OutboundMessage(channel="telegram", chat_id=message.chat_id, content=content)
    )


async def handle(channel, message) -> bool:
    """Handle one authorized Nanobot message before agent processing."""
    envelope = build_envelope(
        channel=message.channel,
        sender_id=message.sender_id,
        chat_id=message.chat_id,
        content=message.content,
        metadata=message.metadata,
        session_key=message.session_key,
    )
    try:
        emitted_terminal = False
        async def forward(line: str) -> None:
            nonlocal emitted_terminal
            if not line.strip():
                return
            event = validate_event(json.loads(line), envelope["request_id"])
            await _send(channel, message, render_event(event))
            emitted_terminal = emitted_terminal or event["type"] in {"completed", "failed", "cancelled"}
        return_code, stderr = await asyncio.wait_for(_run_local(envelope, forward), timeout=600)
        if return_code != 0 and not emitted_terminal:
            detail = stderr.strip() or f"local CoS runner exited with {return_code}"
            await _send(channel, message, f"[failed] Personal CoS runner unavailable: {detail}")
        elif not emitted_terminal:
            await _send(channel, message, "[failed] Personal CoS runner returned no terminal event.")
    except asyncio.TimeoutError:
        await _send(channel, message, "[failed] Personal CoS runner timed out.")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        await _send(channel, message, f"[failed] Personal CoS runner unavailable: {error}")
    return True


if __name__ == "__main__":
    sample = build_envelope(channel="telegram", sender_id="owner", chat_id="1", content="hello")
    assert sample["version"] == "personal.edge.v1"
    assert sample["command"] is False
