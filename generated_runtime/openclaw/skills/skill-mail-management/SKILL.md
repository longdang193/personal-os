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

## Digest Mode

Invoke with `/skill skill-mail-management digest` when the user asks for a mail digest, brief, overview, or organized inbox.

1. Resolve all configured mail accounts unless the user names specific accounts.
2. Use unread mail or messages received during the last 24 hours by default.
3. Fetch metadata first: account, sender, subject, received time, unread state, thread identity, and snippet.
4. Fetch full content only when needed to determine importance, action, deadline, or reply need.
5. Normalize messages across providers before ranking or grouping.
6. Group one combined result into action required, needs reply, important, FYI, and low priority.
7. Rank within groups by deadline, urgency, user impact, then received time.
8. Keep source account visible on every item and report partial provider failures.
9. Summarize suppressed newsletters, promotions, and routine automation by count.
10. Keep digest mode read-only: never mark read, archive, delete, reply, or send.
11. Propose handoffs only for concrete, material follow-ups; do not add them to ordinary FYI mail.
12. Use action IDs only within the current digest and conversation.

For each significant message report account, sender, subject, concise meaning, why it matters, deadline, requested action, reply-needed status, and recommended next step.

## Action Handoffs

When a message implies a concrete follow-up:

1. Identify the required user outcome and evidence supporting it.
2. Select a target domain and operation without assuming every deadline is a calendar event.
3. Return a proposal; never perform unrelated writes during a digest.
4. Preserve account, provider, thread, message, and received-time provenance.
5. Include confidence and missing fields when the target action is incomplete or ambiguous.
6. Let Personal CoS resolve and dispatch the handoff; never call another skill directly.

Possible targets:

- Calendar event or availability check → `calendar-management`.
- Reminder or wake-up → runtime scheduler.
- Reply, draft, archive, or label → `mail-management`.
- Project task or request → `personal-routing`.
- Browser-only action → browser capability.

A deadline may require a calendar event, reminder, project task, mail reply, or no follow-up. Propose only options supported by message evidence.

Use session-scoped IDs such as `A1` and `A1.1`. They are invalid after the digest context ends and require no durable action store.

Logical handoff shape:

```yaml
id: A1.1
target_domain: calendar
operation: create
authorization: proposal
confidence: high
source:
  account: student
  provider: ...
  thread_id: ...
  message_id: ...
  received_at: ...
payload:
  title: ...
  date: ...
  timezone: ...
  notes: ...
```

User approval for one handoff authorizes only that stated operation. Batch requests require a preview and confirmation before multiple writes, attendee notifications, external messages, or destructive changes.

## Authorization

- Read, search, summarize, and draft: act automatically when request is clear.
- Archive or mark read: act automatically for an explicit, unambiguous target.
- Send or reply: require explicit authorization for the exact prepared message.
- Bulk archive, bulk deletion, or external forwarding: confirm before acting.
- If account, recipient, thread, or requested change is ambiguous, ask one focused question.

## Provider Boundary

- Resolve account and provider through `TOOL_REGISTRY.toml` in the runtime workspace.
- Use only tools marked `status = "runtime"`; do not infer availability from an installed CLI.
- For the `student` account, use the registered read-only Himalaya capability and provider account `ovgu`.
- Use `himalaya_mail` with only `list`, `search`, or `read` actions.
- Treat `student` mail as read-only; do not draft, send, archive, delete, or mark messages read through this account.
- Use provider-native authentication and local secret stores.
- Never place provider commands, tokens, credentials, mailbox paths, or private addresses in this skill.
- Do not claim success without provider result evidence.

## Output

For summaries, report account, sender, subject, intent, urgency, deadline, requested action, and next step. Mark unknown facts as unknown.
