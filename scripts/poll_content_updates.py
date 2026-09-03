"""Fetch RSS sources and emit normalized content.update.v1 events."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
import tomllib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    import certifi
except ImportError:
    certifi = None


MAX_FEED_BYTES = 2_000_000
MAX_CONTENT_CHARS = 20_000
MAX_SEEN_EVENTS = 200
DEFAULT_SOURCE_ID = "ovgu-fww-news"
DEFAULT_CONFIG = Path.home() / ".personal-os" / "watch_sources.toml"


def validate_source_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source URL must use http or https")
    return url


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def _field(element: ET.Element, names: set[str]) -> str:
    for child in element:
        if _local_name(child.tag) in names:
            value = child.attrib.get("href", "") or _text(child)
            if value:
                return value.strip()
    return ""


def parse_feed(payload: bytes) -> list[dict[str, str]]:
    if len(payload) > MAX_FEED_BYTES:
        raise ValueError("RSS feed exceeds size limit")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise ValueError(f"invalid RSS or Atom feed: {error}") from error

    items: list[dict[str, str]] = []
    for element in root.iter():
        if _local_name(element.tag) not in {"item", "entry"}:
            continue
        content = _field(element, {"description", "summary", "content", "encoded"})
        items.append(
            {
                "item_id": _field(element, {"guid", "id"}),
                "title": _field(element, {"title"}),
                "url": _field(element, {"link"}),
                "content": content[:MAX_CONTENT_CHARS],
                "published_at": _field(element, {"pubDate", "published", "updated"}),
            }
        )
    return items


def build_events(
    items: list[dict[str, str]],
    source_id: str,
    source_url: str,
    source_type: str = "rss",
    detected_at: str | None = None,
) -> list[dict[str, str]]:
    if not source_id.strip():
        raise ValueError("source ID is required")
    validate_source_url(source_url)
    detected_at = detected_at or datetime.now(timezone.utc).isoformat()
    events: list[dict[str, str]] = []
    for item in items:
        identity = "|".join(item.get(key, "") for key in ("item_id", "url", "title", "published_at"))
        item_id = item.get("item_id") or hashlib.sha256(identity.encode()).hexdigest()[:16]
        content = item.get("content", "")
        events.append(
            {
                "schema": "content.update.v1",
                "event_id": f"{source_id}:{item_id}",
                "source_id": source_id,
                "source_type": source_type,
                "item_id": item_id,
                "url": item.get("url") or source_url,
                "title": item.get("title", ""),
                "content": content,
                "published_at": item.get("published_at", "") or "unknown",
                "detected_at": detected_at,
                "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            }
        )
    return events


def load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"seen_event_ids": []}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid state file: {path}") from error
    if not isinstance(state, dict):
        raise ValueError(f"state file must contain an object: {path}")
    seen = state.get("seen_event_ids", [])
    state["seen_event_ids"] = [value for value in seen if isinstance(value, str)][-MAX_SEEN_EVENTS:]
    return state


def save_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def select_new_events(events: list[dict[str, str]], state: dict[str, object]) -> list[dict[str, str]]:
    seen = list(state.get("seen_event_ids", []))
    seen_ids = set(seen)
    new_events = []
    for event in events:
        event_id = event["event_id"]
        if event_id not in seen_ids:
            new_events.append(event)
            seen.append(event_id)
            seen_ids.add(event_id)
    state["seen_event_ids"] = seen[-MAX_SEEN_EVENTS:]
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    return new_events


def load_source(config_path: Path, source_id: str) -> tuple[str, str, str]:
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"cannot read source config: {config_path}") from error
    for source in config.get("sources", []):
        if source.get("id") == source_id and source.get("enabled", True):
            return source_id, source["type"], validate_source_url(source["url"])
    raise ValueError(f"enabled source not found: {source_id}")


def fetch_feed(url: str, timeout: int) -> bytes:
    request = Request(url, headers={"Accept": "application/rss+xml, application/atom+xml, application/xml", "User-Agent": "personal-os-rss/1"})
    context = ssl.create_default_context(cafile=certifi.where()) if certifi else ssl.create_default_context()
    with urlopen(request, context=context, timeout=timeout) as response:
        payload = response.read(MAX_FEED_BYTES + 1)
    if len(payload) > MAX_FEED_BYTES:
        raise ValueError("RSS feed exceeds size limit")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-id", default=DEFAULT_SOURCE_ID)
    parser.add_argument("--url")
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--bootstrap", action="store_true", help="Record current items without emitting them.")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--max-items", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        source_id = args.source_id
        source_type = "rss"
        source_url = args.url
        if not source_url:
            source_id, source_type, source_url = load_source(args.config, source_id)
        validate_source_url(source_url)
        state_path = args.state_file or (Path.home() / ".personal-os" / "content-state" / f"{source_id}.json")
        state = load_state(state_path)
        events = build_events(
            parse_feed(fetch_feed(source_url, args.timeout))[: args.max_items],
            source_id,
            source_url,
            source_type,
        )
        new_events = select_new_events(events, state)
        save_state(state_path, state)
        if not args.bootstrap:
            for event in new_events:
                print(json.dumps(event, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"poll_content_updates: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
