---
name: skill-calendar-management
description: Use when reading, searching, planning, creating, updating, or canceling personal calendar events and availability.
---

# Calendar Management

Manage calendar events and availability. Keep calendar semantics separate from
provider APIs and from reminder scheduling.

## Workflow

1. Identify calendar scope, event identity, participants, location, timezone, and requested change.
2. Read relevant events and availability before proposing or applying changes.
3. Check conflicts, travel, preparation time, recurrence, and attendee impact.
4. Clarify missing event identity, date, time, timezone, or intended calendar.
5. Apply only the requested event change and report result or blocker.

## Operations

- Read: list calendars, events, event details, attendees, and recurrence.
- Search: find events by time range, participant, title, or location.
- Availability: check free/busy before proposing a time.
- Create: add an event with explicit time, timezone, participants, and location.
- Update: change only requested fields and preserve unrelated event details.
- Cancel: remove an event only after confirming identity and attendee impact.

## Authorization

- Read, search, and conflict checks: act automatically when request is clear.
- Create or update: act when event, time, timezone, and target calendar are unambiguous.
- Ambiguous event or time: ask one focused clarification question.
- Cancellation with attendees, external notifications, or bulk changes: confirm first.
- Preserve existing commitments unless user explicitly requests a change.

## Calendar Versus Reminder

- A calendar event records an appointment, meeting, or commitment.
- A reminder records a future prompt or wake-up job.
- Route reminders to the runtime scheduler; do not create calendar events for reminders unless requested.

## Provider Boundary

- Resolve calendar and provider through configured runtime metadata; source registry is `repo_config/tool_registry.toml`.
- Use provider-native authentication and local secret stores.
- Never place provider commands, tokens, credentials, or calendar-specific API syntax in this skill.
- Do not claim success without provider result evidence.
