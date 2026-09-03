"""Fetch configured content sources and emit content.update.v1 events."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
import tomllib
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
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
DEFAULT_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
APIFY_API_URL = "https://api.apify.com/v2/acts/apify~instagram-post-scraper/run-sync-get-dataset-items"
MAX_APIFY_BYTES = 5_000_000


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


def build_apify_events(
    items: list[dict[str, object]],
    source_id: str,
    target: str,
    detected_at: str | None = None,
) -> list[dict[str, str]]:
    source_url = target if target.startswith(("http://", "https://")) else f"https://www.instagram.com/{target.strip('@').strip('/')}/"
    normalized: list[dict[str, str]] = []
    for item in items:
        owner = str(item.get("ownerUsername") or item.get("username") or target).strip()
        item_id = str(item.get("id") or item.get("shortCode") or item.get("shortcode") or "").strip()
        url = str(item.get("url") or item.get("postUrl") or "").strip()
        if not item_id and not url:
            continue
        normalized.append(
            {
                "item_id": item_id,
                "url": url,
                "title": f"@{owner.lstrip('@')} posted on Instagram",
                "content": str(item.get("caption") or "")[:MAX_CONTENT_CHARS],
                "published_at": str(item.get("timestamp") or "unknown"),
            }
        )
    return build_events(normalized, source_id, source_url, "social", detected_at)


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


def load_sources(config_path: Path, source_id: str | None = None) -> list[dict[str, object]]:
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"cannot read source config: {config_path}") from error
    sources = [source for source in config.get("sources", []) if source.get("enabled", True)]
    if source_id:
        sources = [source for source in sources if source.get("id") == source_id]
        if not sources:
            raise ValueError(f"enabled source not found: {source_id}")
    if not sources:
        raise ValueError(f"no enabled sources found: {config_path}")
    for source in sources:
        source_type = source.get("type")
        if source_type == "rss":
            validate_source_url(str(source["url"]))
        elif source_type == "social" and source.get("provider") in {"apify", "apify-instagram"}:
            if source.get("platform", "instagram") != "instagram" or not str(source.get("target", "")).strip():
                raise ValueError(f"invalid Apify Instagram source: {source.get('id', '<unknown>')}")
        else:
            raise ValueError(f"unsupported source type: {source_type}")
    return sources


def fetch_feed(url: str, timeout: int) -> bytes:
    request = Request(url, headers={"Accept": "application/rss+xml, application/atom+xml, application/xml", "User-Agent": "personal-os-rss/1"})
    context = ssl.create_default_context(cafile=certifi.where()) if certifi else ssl.create_default_context()
    with urlopen(request, context=context, timeout=timeout) as response:
        payload = response.read(MAX_FEED_BYTES + 1)
    if len(payload) > MAX_FEED_BYTES:
        raise ValueError("RSS feed exceeds size limit")
    return payload


def load_env_value(path: Path, name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in lines:
        key, separator, candidate = line.partition("=")
        if separator and key.strip() == name:
            candidate = candidate.strip()
            if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in {"'", '"'}:
                candidate = candidate[1:-1]
            return candidate.strip()
    return ""


def _target_name(target: str) -> str:
    parsed = urlparse(target)
    value = parsed.path.strip("/").split("/")[-1] if parsed.path else target
    return value.lstrip("@").lower()


def _item_owner(item: dict[str, object]) -> str:
    owner = item.get("ownerUsername") or item.get("username")
    if isinstance(owner, str):
        return _target_name(owner)
    return ""


def _cutoff_from_state(state: dict[str, object]) -> datetime | None:
    value = state.get("updated_at")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc) - timedelta(minutes=10)


def fetch_apify_items(
    targets: list[str],
    cutoff: str,
    token: str,
    max_items: int,
    timeout: int,
) -> list[dict[str, object]]:
    if not token:
        raise ValueError("APIFY_TOKEN is required for Apify sources")
    payload = json.dumps(
        {
            "username": targets,
            "resultsLimit": max_items,
            "skipPinnedPosts": True,
            "onlyPostsNewerThan": cutoff,
            "dataDetailLevel": "basicData",
        }
    ).encode("utf-8")
    request = Request(
        APIFY_API_URL,
        data=payload,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "personal-os-content/1",
        },
        method="POST",
    )
    context = ssl.create_default_context(cafile=certifi.where()) if certifi else ssl.create_default_context()
    with urlopen(request, context=context, timeout=timeout) as response:
        result = response.read(MAX_APIFY_BYTES + 1)
    if len(result) > MAX_APIFY_BYTES:
        raise ValueError("Apify response exceeds size limit")
    decoded = json.loads(result)
    if not isinstance(decoded, list) or not all(isinstance(item, dict) for item in decoded):
        raise ValueError("Apify response must contain an array of objects")
    return decoded


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-id")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--url")
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--bootstrap", action="store_true", help="Record current items without emitting them.")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--max-items", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.url:
            sources = [{"id": args.source_id or DEFAULT_SOURCE_ID, "type": "rss", "url": args.url}]
        else:
            sources = load_sources(args.config, args.source_id)

        def state_path_for(source_id: str) -> Path:
            if args.state_file and len(sources) == 1:
                return args.state_file
            return Path.home() / ".personal-os" / "content-state" / f"{source_id}.json"

        def emit(source_id: str, events: list[dict[str, str]], state_path: Path) -> None:
            state = load_state(state_path)
            new_events = select_new_events(events, state)
            save_state(state_path, state)
            if not args.bootstrap:
                for event in new_events:
                    print(json.dumps(event, ensure_ascii=False))

        apify_sources = [source for source in sources if source.get("type") == "social"]
        for source in [source for source in sources if source.get("type") == "rss"]:
            source_id = str(source["id"])
            source_url = validate_source_url(str(source["url"]))
            state_path = state_path_for(source_id)
            events = build_events(
                parse_feed(fetch_feed(source_url, args.timeout))[: args.max_items],
                source_id,
                source_url,
                "rss",
            )
            emit(source_id, events, state_path)

        if apify_sources:
            states = {
                str(source["id"]): load_state(state_path_for(str(source["id"])))
                for source in apify_sources
            }
            cutoffs = [_cutoff_from_state(state) for state in states.values()]
            cutoff = min((value for value in cutoffs if value), default=datetime.now(timezone.utc) - timedelta(days=1))
            token = load_env_value(args.env_file, "APIFY_TOKEN")
            targets = [str(source["target"]) for source in apify_sources]
            items = fetch_apify_items(targets, cutoff.isoformat().replace("+00:00", "Z"), token, args.max_items, args.timeout)
            for source in apify_sources:
                source_id = str(source["id"])
                target = str(source["target"])
                target_name = _target_name(target)
                matching = items if len(apify_sources) == 1 else [item for item in items if _item_owner(item) == target_name]
                state_path = state_path_for(source_id)
                emit(source_id, build_apify_events(matching, source_id, target), state_path)
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"poll_content_updates: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
