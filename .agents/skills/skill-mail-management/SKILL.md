---
name: skill-mail-management
description: Use when checking, searching, reading, triaging, drafting, replying to, or sending personal email across configured accounts.
---

# Mail Management

Manage email by intent, account, thread, and authorization. Keep mail behavior
independent from provider commands and authentication details.

## Workflow

1. Identify requested account scope: one account or all configured accounts.
2. Search or list messages using the narrowest useful query.
3. Read the relevant thread and attachments when needed.
4. Extract sender, intent, urgency, deadlines, requested action, and open questions.
5. Separate message facts from recommendations or inferences.
6. Perform only the requested write action and report result or blocker.

## Operations

- Read: list inbox or unread mail, search, open messages or threads, inspect attachments.
- Reason: classify sender, intent, urgency, deadline, requested action, and sensitivity.
- Draft: compose new mail or reply while preserving thread context and user voice.
- Manage: mark read, archive, or apply labels only when target and effect are clear.
- Send: send only after user authorization covers exact recipient, content, and attachments.

## Authorization

- Read, search, summarize, and draft: act automatically when request is clear.
- Archive or mark read: act automatically for an explicit, unambiguous target.
- Send or reply: require explicit authorization for the exact prepared message.
- Bulk archive, bulk deletion, or external forwarding: confirm before acting.
- If account, recipient, thread, or requested change is ambiguous, ask one focused question.

## Provider Boundary

- Resolve account and provider through configured runtime metadata; source registry is `repo_config/tool_registry.toml`.
- Use provider-native authentication and local secret stores.
- Never place provider commands, tokens, credentials, mailbox paths, or private addresses in this skill.
- Do not claim success without provider result evidence.

## Output

For summaries, report account, sender, subject, intent, urgency, deadline, requested action, and next step. Mark unknown facts as unknown.
