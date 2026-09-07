"""Read-only provider-neutral mail MCP server."""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations


MAX_LIMIT = 50
MAX_QUERY_LENGTH = 500
MESSAGE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,256}$")
REGISTRY_PATH = Path(__file__).resolve().parents[1] / "repo_config" / "tool_registry.toml"
ENV_PATH = REGISTRY_PATH.parents[1] / ".env"
READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)

mcp = FastMCP(
    "personal-os-mail",
    instructions="Read-only mail search and read bridge. Never sends, archives, deletes, or marks mail read.",
    log_level="ERROR",
)


def _load_repo_env() -> None:
    if not ENV_PATH.is_file():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$", line)
        if match and match.group(1) not in os.environ:
            os.environ[match.group(1)] = match.group(2).strip().strip('"').strip("'")


class MailBridgeError(RuntimeError):
    """Safe provider error for MCP clients."""


def _validate_query(query: str) -> str:
    if not isinstance(query, str) or len(query) > MAX_QUERY_LENGTH or "\x00" in query:
        raise ValueError(f"query must be text of at most {MAX_QUERY_LENGTH} characters")
    return query.strip()


def _validate_limit(limit: int) -> int:
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be an integer from 1 to {MAX_LIMIT}")
    return limit


def _validate_account(account: str, *, allow_all: bool = True) -> str:
    allowed = set(_mail_accounts()) | ({"all"} if allow_all else set())
    if account not in allowed:
        raise ValueError(f"account must be one of: {', '.join(sorted(allowed))}")
    return account


def _validate_message_id(message_id: str) -> str:
    if not isinstance(message_id, str) or not MESSAGE_ID_PATTERN.fullmatch(message_id):
        raise ValueError("message_id contains unsupported characters")
    return message_id


def _mail_accounts() -> tuple[str, ...]:
    registry = tomllib.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return tuple(
        account["id"]
        for account in registry.get("accounts", [])
        if account.get("domain") == "mail" and isinstance(account.get("id"), str)
    )


def _account_config(account: str) -> dict[str, Any]:
    registry = tomllib.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    for item in registry.get("accounts", []):
        if item.get("id") == account and item.get("domain") == "mail":
            if item.get("tool") != "mail-runtime" or not item.get("provider"):
                break
            return item
    raise MailBridgeError(f"mail account is not registered: {account}")


def _command_result(command: list[str]) -> Any:
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
        raise MailBridgeError("mail provider command is not installed") from error
    except subprocess.TimeoutExpired as error:
        raise MailBridgeError("mail provider command timed out") from error
    if completed.returncode:
        output = f"{completed.stdout}\n{completed.stderr}".lower()
        detail = (
            "provider authentication failed"
            if any(term in output for term in ("auth", "credential", "token", "password"))
            else f"exit code {completed.returncode}"
        )
        raise MailBridgeError(f"mail provider command failed: {detail}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise MailBridgeError("mail provider returned invalid JSON") from error


def _gws_command() -> list[str]:
    executable = shutil.which("gws.ps1") or shutil.which("gws")
    if not executable:
        raise MailBridgeError("Google Workspace provider command is not installed")
    return ["powershell.exe", "-NoProfile", "-File", executable] if executable.lower().endswith(".ps1") else [executable]


def _gws_call(operation: str, params: dict[str, Any]) -> Any:
    return _command_result(
        _gws_command()
        + [
            "gmail",
            "users",
            "messages",
            operation,
            "--params",
            json.dumps(params, separators=(",", ":")),
            "--format",
            "json",
        ]
    )


def _himalaya_command() -> str:
    executable = shutil.which("himalaya")
    if not executable:
        raise MailBridgeError("Himalaya provider command is not installed")
    return executable


def _himalaya_call(account_name: str, arguments: list[str]) -> Any:
    account = _account_config(account_name)
    return _command_result(
        [
            _himalaya_command(),
            "--account",
            str(account.get("provider_account", "")),
            *arguments,
            "--json",
            "--log-level",
            "off",
        ]
    )


def _header_map(message: dict[str, Any]) -> dict[str, str]:
    headers = message.get("payload", {}).get("headers", [])
    return {
        str(header.get("name", "")).lower(): str(header.get("value", ""))
        for header in headers
        if isinstance(header, dict) and header.get("name")
    }


def _decode_body(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")
    except (ValueError, UnicodeError):
        return ""


def _gmail_text(payload: dict[str, Any]) -> str:
    body = payload.get("body", {})
    if isinstance(body, dict) and body.get("data") and payload.get("mimeType") == "text/plain":
        return _decode_body(str(body["data"]))
    for part in payload.get("parts", []) if isinstance(payload, dict) else []:
        if isinstance(part, dict):
            text = _gmail_text(part)
            if text:
                return text
    return ""


def _normalize_gmail(message: dict[str, Any], *, include_body: bool) -> dict[str, Any]:
    headers = _header_map(message)
    normalized = {
        "id": message.get("id"),
        "thread_id": message.get("threadId"),
        "date": headers.get("date"),
        "from": headers.get("from"),
        "to": headers.get("to"),
        "cc": headers.get("cc"),
        "subject": headers.get("subject"),
        "snippet": message.get("snippet"),
        "labels": message.get("labelIds", []),
    }
    if include_body:
        normalized["body"] = _gmail_text(message.get("payload", {}))
    return normalized


def _as_envelopes(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("envelopes", "messages", "items", "data"):
            if isinstance(payload.get(key), list):
                return [item for item in payload[key] if isinstance(item, dict)]
    return []


def _normalize_himalaya(envelope: dict[str, Any]) -> dict[str, Any]:
    source = envelope.get("envelope") if isinstance(envelope.get("envelope"), dict) else envelope
    return {
        "id": envelope.get("id") or envelope.get("uid") or source.get("id"),
        "date": source.get("date") or envelope.get("date"),
        "from": source.get("from") or envelope.get("from"),
        "to": source.get("to") or envelope.get("to"),
        "subject": source.get("subject") or envelope.get("subject"),
        "flags": envelope.get("flags", []),
        "snippet": envelope.get("preview") or envelope.get("snippet"),
    }


def _search_personal(account_name: str, query: str, limit: int) -> dict[str, Any]:
    account = _account_config(account_name)
    if account["provider"] != "google-workspace":
        raise MailBridgeError("personal mail provider is not configured for Google Workspace")
    params = {"userId": "me", "maxResults": limit}
    if query:
        params["q"] = query
    result = _gws_call("list", params)
    messages = result.get("messages", []) if isinstance(result, dict) else []
    normalized = []
    for item in messages[:limit]:
        message_id = _validate_message_id(str(item.get("id", "")))
        metadata = _gws_call(
            "get",
            {
                "userId": "me",
                "id": message_id,
                "format": "metadata",
                "metadataHeaders": ["Date", "From", "To", "Cc", "Subject"],
            },
        )
        normalized.append(_normalize_gmail(metadata, include_body=False))
    return {"account": account_name, "provider": account["provider"], "messages": normalized, "count": len(normalized)}


def _search_student(account_name: str, query: str, limit: int) -> dict[str, Any]:
    account = _account_config(account_name)
    if account["provider"] != "himalaya":
        raise MailBridgeError("student mail provider is not configured for Himalaya")
    arguments = ["envelope", "search"]
    if query:
        arguments.append(query)
    result = _himalaya_call(account_name, arguments + ["--page-size", str(limit)])
    normalized = [_normalize_himalaya(item) for item in _as_envelopes(result)[:limit]]
    return {"account": account_name, "provider": account["provider"], "messages": normalized, "count": len(normalized)}


def _search_one(account: str, query: str, limit: int) -> dict[str, Any]:
    provider = _account_config(account)["provider"]
    if provider == "google-workspace":
        return _search_personal(account, query, limit)
    if provider == "himalaya":
        return _search_student(account, query, limit)
    raise MailBridgeError(f"unsupported mail provider: {provider}")


@mcp.tool(
    name="mail.search",
    description="Search personal or student mail. Read-only; query syntax follows each registered provider.",
    annotations=READ_ONLY,
)
def mail_search(account: str = "all", query: str = "", limit: int = 20) -> dict[str, Any]:
    """Search configured mail accounts without changing message state."""
    account = _validate_account(account)
    query = _validate_query(query)
    limit = _validate_limit(limit)
    accounts = _mail_accounts() if account == "all" else (account,)
    results: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    for selected in accounts:
        try:
            results.append(_search_one(selected, query, limit))
        except MailBridgeError as error:
            if account != "all":
                raise
            errors[selected] = str(error)
    return {"accounts": list(accounts), "results": results, "errors": errors}


def _read_personal(account_name: str, message_id: str) -> dict[str, Any]:
    return _normalize_gmail(_gws_call("get", {"userId": "me", "id": message_id, "format": "full"}), include_body=True)


def _read_student(account_name: str, message_id: str) -> dict[str, Any]:
    result = _himalaya_call(account_name, ["message", "read", message_id])
    if isinstance(result, dict) and isinstance(result.get("message"), dict):
        result = result["message"]
    normalized = _normalize_himalaya(result if isinstance(result, dict) else {})
    if isinstance(result, dict):
        normalized["body"] = result.get("body") or result.get("text") or result.get("content")
    return normalized


@mcp.tool(
    name="mail.read",
    description="Read one message from personal or student mail without marking it read.",
    annotations=READ_ONLY,
)
def mail_read(account: str, message_id: str) -> dict[str, Any]:
    """Read one configured message without changing message state."""
    account = _validate_account(account, allow_all=False)
    message_id = _validate_message_id(message_id)
    provider = _account_config(account)["provider"]
    if provider == "google-workspace":
        message = _read_personal(account, message_id)
    elif provider == "himalaya":
        message = _read_student(account, message_id)
    else:
        raise MailBridgeError(f"unsupported mail provider: {provider}")
    return {"account": account, "provider": provider, "message": message}


if __name__ == "__main__":
    _load_repo_env()
    mcp.run("stdio")
