---
name: skill-daily-planner
description: Plan, capture, and review daily work using Obsidian Markdown as the single source of truth.
---

# SSOT Daily Planner

Use Obsidian Markdown as the only durable task and planning state. Do not create
or use a planner database, runtime memory, `~/planner/`, or a second task list.

## Inputs

Resolve these before planning:

- current local date and time
- explicit IANA timezone from runtime configuration
- `OBSIDIAN_VAULT_ROOT` from runtime-local configuration
- open tasks and commitments in the vault
- calendar events and free time when calendar read capability exists
- user constraints such as available hours, energy, location, and fixed work

If vault access is unavailable, return a read-only plan from supplied context
and state that no Obsidian write occurred. If timezone is missing, ask for it;
never infer it from machine location.

## SSOT Layout

Use these vault-relative paths:

- `Planner/Inbox.md`: uncategorized capture
- `Planner/Commitments.md`: work promised to another person or organization
- `Daily/YYYY-MM-DD.md`: schedule, review, and planning snapshot
- existing project notes: project-owned tasks

Do not move tasks into a central task file merely to make planning easier.
Search existing project notes first and preserve source-note ownership.

## Task Contract

Write one Markdown checkbox per durable task:

```markdown
- [ ] Review German material 📅 2026-09-08 #area/german
- [ ] Submit application 📅 2026-09-12 ⏫
- [ ] Water plants 🔁 every week 📅 2026-09-13
```

Rules:

- use `YYYY-MM-DD` for due dates
- add due date only when user supplied or approved a date
- use recurrence only when the user requested recurring work
- use priority only when user supplied or approved priority
- preserve task text, tags, links, and unrelated metadata
- treat duplicate task text as ambiguous when source note or date differs
- identify tasks by source path plus exact task text; ask when identity is unclear

Obsidian Tasks is query and status UI. It does not become a second planner
state store. Daily-note snapshots never become authoritative task copies.

## Commands

### Plan today

1. Read open tasks, overdue tasks, commitments, and today's calendar.
2. Separate fixed events from flexible work.
3. Surface overdue items, deadline conflicts, missing information, and blocked work.
4. Select at most three priorities using deadlines, commitments, user intent,
   and available capacity. Do not invent urgency.
5. Build schedule blocks around fixed events and leave recovery or transition
   time. Never promise more work than available capacity supports.
6. Render a plan preview with Top 3, schedule, conflicts, carry-forward, and
   blocked items.
7. Write only the managed section of `Daily/YYYY-MM-DD.md` when the user asks
   to save the plan or when an authorized scheduled run explicitly permits it.

### Plan tomorrow

Use same workflow for next local date. Do not reschedule unfinished work
automatically; show proposed carry-forward first.

### Capture

1. Preserve user's wording unless clarification is needed.
2. Search `Planner/Inbox.md` and relevant source notes for exact duplicates.
3. Append one checkbox to `Planner/Inbox.md` only after exact-dedupe succeeds.
4. Do not assign due date, priority, project, or recurrence without user input.
5. If matching tasks are ambiguous, show candidates and ask one focused question.

### Review

Report completed, open, overdue, blocked, and carried-forward work from source
notes. Propose changes; do not bulk move, complete, delete, or reprioritize
tasks without explicit confirmation.

## Managed Daily Notes

Own only the content between these exact markers:

```markdown
<!-- daily-planner:managed:start -->
<!-- daily-planner:managed:end -->
```

Preserve all content outside markers. If markers are absent, append one managed
block after existing content. If multiple marker pairs exist, stop and report
ambiguous note structure. Repeating the same plan must replace one block, not
append duplicates.

Use this block shape:

```markdown
<!-- daily-planner:managed:start -->
## Daily Plan

### Top 3
- Task snapshot or source-note link

### Schedule
- 09:00–10:30 Deep work — topic

### Conflicts
- None

### Carry Forward
- None

### Blocked
- None

### Evening Review
- Completed:
- Carry forward:
- Blocked:
<!-- daily-planner:managed:end -->
```

Task snapshots are informational. Completion and rescheduling always target
the source task, never the snapshot.

## Authorization

- reading vault tasks and calendar events: automatic when scope is clear
- saving a managed daily plan: automatic only for explicit request or authorized scheduled run
- capturing a task: allowed when user explicitly asks to capture it
- completing, deleting, reprioritizing, assigning dates, changing recurrence,
  or moving tasks: explicit user intent required
- bulk changes, commitment writes, calendar writes, and external reminders:
  preview and confirm first
- never mark work complete because conversation implies completion
- never claim a write without result evidence

## Runtime Compatibility

Use runtime-provided file, calendar, and scheduler capabilities. Keep provider
commands, tokens, credentials, installation commands, and runtime-specific tool
names outside this skill.

Nanobot requests may arrive through its relay boundary. Do not bypass that
boundary or add personal task tools to a relay-only runtime. OpenClaw and Hermes
may execute this skill locally when their configured capabilities permit it;
the workflow and file contract remain identical.

## Failure Handling

Report the first missing or failed dependency with:

- capability or file involved
- operation not completed
- data already changed, if any
- safe next action

Never overwrite a note after parse ambiguity, path escape, marker conflict, or
partial read. Preserve original error context and leave user data unchanged
when a safe write cannot be proven.
