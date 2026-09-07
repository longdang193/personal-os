"""Provider-neutral Google Calendar MCP server for Personal OS."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations


MAX_LIMIT = 2500
MAX_IDS = 50
MAX_QUERY_LENGTH = 500
MAX_EVENT_BYTES = 100_000
ID_PATTERN = re.compile(r"^[A-Za-z0-9_.@:#-]{1,512}$")
RFC3339_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
REGISTRY_PATH = Path(__file__).resolve().parents[1] / "repo_config" / "tool_registry.toml"
READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
WRITE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)

mcp = FastMCP(
    "personal-os-calendar",
    instructions=(
        "Google Calendar bridge. Reads and writes only the registered Google Calendar account. "
        "Use read/search/free-busy before changing events. Preserve unspecified event fields."
    ),
    log_level="ERROR",
)


class CalendarBridgeError(RuntimeError):
    """Safe provider error for MCP clients."""


def _calendar_account() -> dict[str, Any]:
    registry = tomllib.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    for account in registry.get("accounts", []):
        if account.get("domain") == "calendar" and account.get("id") == "google-calendar":
            return account
    raise CalendarBridgeError("Google Calendar account is not registered")


def _gws_command() -> list[str]:
    executable = shutil.which("gws.ps1") or shutil.which("gws")
    if not executable:
        raise CalendarBridgeError("Google Workspace provider command is not installed")
    return ["powershell.exe", "-NoProfile", "-File", executable] if executable.lower().endswith(".ps1") else [executable]


def _gws_call(resource_method: str, *, params: dict[str, Any] | None = None, body: dict[str, Any] | None = None) -> Any:
    _calendar_account()
    command = _gws_command() + resource_method.split()
    if params:
        command += ["--params", json.dumps(params, ensure_ascii=False)]
    if body is not None:
        command += ["--json", json.dumps(body, ensure_ascii=False)]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    except FileNotFoundError as error:
        raise CalendarBridgeError("Google Calendar provider command is not installed") from error
    except subprocess.TimeoutExpired as error:
        raise CalendarBridgeError("Google Calendar provider command timed out") from error
    if completed.returncode:
        output = f"{completed.stdout}\n{completed.stderr}".lower()
        detail = (
            "provider authentication failed"
            if any(term in output for term in ("auth", "credential", "token", "permission"))
            else f"exit code {completed.returncode}"
        )
        raise CalendarBridgeError(f"Google Calendar provider command failed: {detail}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise CalendarBridgeError("Google Calendar provider returned invalid JSON") from error


def _validate_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise ValueError(f"{field} contains unsupported characters")
    return value


def _validate_limit(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= MAX_LIMIT:
        raise ValueError(f"limit must be an integer from 1 to {MAX_LIMIT}")
    return value


def _validate_query(value: str) -> str:
    if not isinstance(value, str) or len(value) > MAX_QUERY_LENGTH or "\x00" in value:
        raise ValueError(f"query must be text of at most {MAX_QUERY_LENGTH} characters")
    return value.strip()


def _validate_time(value: str, field: str) -> str:
    if not isinstance(value, str) or not RFC3339_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must be an RFC3339 timestamp with timezone")
    return value


def _validate_event(event: dict[str, Any], *, require_time: bool) -> dict[str, Any]:
    if not isinstance(event, dict) or not event:
        raise ValueError("event must be a non-empty object")
    encoded = json.dumps(event, ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_EVENT_BYTES:
        raise ValueError("event exceeds size limit")
    if require_time and not all(field in event for field in ("start", "end")):
        raise ValueError("event must contain start and end")
    for field in ("start", "end"):
        if field not in event:
            continue
        value = event.get(field)
        if not isinstance(value, dict) or not (value.get("dateTime") or value.get("date")):
            raise ValueError(f"event.{field} must contain dateTime or date")
        if value.get("dateTime"):
            _validate_time(value["dateTime"], f"event.{field}.dateTime")
    return event


def _validate_send_updates(value: str) -> str:
    if value not in {"all", "externalOnly", "none"}:
        raise ValueError("send_updates must be all, externalOnly, or none")
    return value


@mcp.tool(
    name="calendar.list_calendars",
    description="List calendars available to the registered Google Calendar account.",
    annotations=READ_ONLY,
)
def calendar_list_calendars(limit: int = 100) -> dict[str, Any]:
    """List accessible calendars without changing state."""
    return _gws_call(
        "calendar calendarList list",
        params={"maxResults": _validate_limit(limit)},
    )


@mcp.tool(
    name="calendar.search",
    description="Search or list Google Calendar events in a time range without changing state.",
    annotations=READ_ONLY,
)
def calendar_search(
    calendar_id: str = "primary",
    time_min: str = "",
    time_max: str = "",
    query: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    """Search events by time range, text, location, or participant."""
    params: dict[str, Any] = {
        "calendarId": _validate_id(calendar_id, "calendar_id"),
        "maxResults": _validate_limit(limit),
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if time_min:
        params["timeMin"] = _validate_time(time_min, "time_min")
    if time_max:
        params["timeMax"] = _validate_time(time_max, "time_max")
    if query:
        params["q"] = _validate_query(query)
    return _gws_call("calendar events list", params=params)


@mcp.tool(
    name="calendar.read",
    description="Read one Google Calendar event by calendar and event ID without changing state.",
    annotations=READ_ONLY,
)
def calendar_read(calendar_id: str, event_id: str) -> dict[str, Any]:
    """Read one event without changing state."""
    return _gws_call(
        "calendar events get",
        params={
            "calendarId": _validate_id(calendar_id, "calendar_id"),
            "eventId": _validate_id(event_id, "event_id"),
        },
    )


@mcp.tool(
    name="calendar.free_busy",
    description="Check Google Calendar free/busy information for a time range.",
    annotations=READ_ONLY,
)
def calendar_free_busy(
    time_min: str,
    time_max: str,
    calendar_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Read free/busy state without changing calendars."""
    if not isinstance(calendar_ids, list) or not 1 <= len(calendar_ids) <= MAX_IDS:
        raise ValueError(f"calendar_ids must contain 1 to {MAX_IDS} calendar IDs")
    return _gws_call(
        "calendar freebusy query",
        body={
            "timeMin": _validate_time(time_min, "time_min"),
            "timeMax": _validate_time(time_max, "time_max"),
            "items": [{"id": _validate_id(calendar_id, "calendar_id")} for calendar_id in calendar_ids],
        },
    )


@mcp.tool(
    name="calendar.write",
    description="Create, update, or cancel one Google Calendar event. Update body contains only requested fields.",
    annotations=WRITE,
)
def calendar_write(
    operation: str,
    calendar_id: str = "primary",
    event_id: str = "",
    event: dict[str, Any] | None = None,
    send_updates: str = "none",
) -> dict[str, Any]:
    """Apply one explicit calendar event change."""
    operation = operation.strip().lower()
    calendar_id = _validate_id(calendar_id, "calendar_id")
    send_updates = _validate_send_updates(send_updates)
    if operation == "create":
        if event is None:
            raise ValueError("event is required for create")
        return _gws_call(
            "calendar events insert",
            params={"calendarId": calendar_id, "sendUpdates": send_updates},
            body=_validate_event(event, require_time=True),
        )
    if operation == "update":
        if not event:
            raise ValueError("event is required for update")
        return _gws_call(
            "calendar events patch",
            params={
                "calendarId": calendar_id,
                "eventId": _validate_id(event_id, "event_id"),
                "sendUpdates": send_updates,
            },
            body=_validate_event(event, require_time=False),
        )
    if operation == "cancel":
        return _gws_call(
            "calendar events delete",
            params={
                "calendarId": calendar_id,
                "eventId": _validate_id(event_id, "event_id"),
                "sendUpdates": send_updates,
            },
        )
    raise ValueError("operation must be create, update, or cancel")


if __name__ == "__main__":
    mcp.run("stdio")
