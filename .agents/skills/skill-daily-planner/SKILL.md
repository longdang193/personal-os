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
- `OBSIDIAN_VAULT` from runtime-local configuration
- open tasks and commitments in the vault
- calendar events and free time when calendar read capability exists
- the target daily note and its managed `Schedule` and `Reminders` sections
- calendar and reminder capability through the runtime tool registry
- user constraints such as available hours, energy, location, and fixed work

If vault access is unavailable, return a read-only plan from supplied context
and state that no Obsidian write occurred. If timezone is missing, ask for it;
never infer it from machine location. Never use repository root, current working
directory, active file path, or a developer-provided path as vault root.

## SSOT Layout

Use these vault-relative paths:

- `Planner/Inbox.md`: uncategorized capture
- `Planner/Commitments.md`: work promised to another person or organization
- `Daily/YYYY-MM-DD.md`: schedule, review, and planning snapshot
- existing project notes: project-owned tasks

Do not move tasks into a central task file merely to make planning easier.
Search existing project notes first and preserve source-note ownership.

The daily note is the only durable source for schedule and reminder intent.
Google Calendar and the runtime scheduler are projections, not alternate
sources of truth. External IDs may be stored as hidden comments beside managed
entries for idempotent updates.

If `Planner/` or `Planner/Inbox.md` is missing, create only those paths inside
the resolved `OBSIDIAN_VAULT`. Do not create a folder relative to repository
root, current working directory, active file path, or any developer-provided
path. If the resolved vault is missing or not a directory, stop without writes.

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

Obsidian Tasks query blocks are the daily-note presentation layer. They read
and update source Markdown tasks; do not copy task lines into daily notes.

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

### Sync today

1. Read only the managed `Daily/YYYY-MM-DD.md` block; do not infer events or
   reminders from arbitrary prose, task queries, or headings outside the block.
2. Parse schedule entries using `- YYYY-MM-DD HH:MM–HH:MM | Event title` and
   reminder entries using `- YYYY-MM-DD HH:MM | Reminder text`.
3. Require an explicit runtime timezone and target calendar. Reject malformed,
   ambiguous, or timezone-less entries without writes.
4. Search existing calendar events and scheduler reminders by stored external
   ID, then stable source identity. Produce one preview containing creates,
   updates, unchanged entries, and orphaned external items.
5. Ask for one confirmation before external writes. Apply only confirmed
   creates and updates, then write returned IDs beside managed entries.

Store linkage as inline comments: `<!-- personal-os:calendar-id=ID -->` or
`<!-- personal-os:reminder-id=ID -->`. When replacing a managed plan, preserve
each linkage comment with its matching normalized entry; never discard it as
template content.

Removing a source entry does not cancel its external projection automatically;
report it as orphaned and require confirmation before cancellation. Calendar
and reminder sync use the same parse, compare, preview, confirm, apply, and
report lifecycle, while retaining their separate provider semantics.

## Managed Daily Notes

Own only the content between these exact markers:

```markdown
<!-- daily-planner:managed:start -->
<!-- daily-planner:managed:end -->
```

Preserve all content outside markers. If markers are absent, append one managed
block after existing content. If multiple marker pairs exist, stop and report
ambiguous note structure. Repeating the same plan must replace one block, not
append duplicates. Preserve matching `personal-os:*-id` linkage comments during
replacement.

Use this block shape:

```markdown
<!-- daily-planner:managed:start -->
# Daily Plan — 2026-09-08

### Top 3
````tasks
not done
due today
sort by priority
sort by due
limit 3
````

### Schedule
<!-- Calendar entries:
- YYYY-MM-DD HH:MM–HH:MM | Event title
-->

### Conflicts
- None

### Reminders
<!-- Reminder entries:
- YYYY-MM-DD HH:MM | Reminder text
-->

### Carry Forward
````tasks
not done
due before today
sort by due
limit 20
````

### Blocked
- None

### Evening Review
- [ ] Record completed work
- [ ] Confirm carry-forward tasks
- [ ] Record blocked tasks
<!-- daily-planner:managed:end -->
```

Use official Obsidian Tasks task syntax for every actionable task: `- [ ]`,
`📅 YYYY-MM-DD`, `🔁` recurrence, and supported priority markers. Use official
````tasks```` query blocks for live task lists. Never invent query keywords.
Completion and rescheduling update the source task returned by the query.

## Authorization

- reading vault tasks and calendar events: automatic when scope is clear
- saving a managed daily plan: automatic only for explicit request or authorized scheduled run
- capturing a task: allowed when user explicitly asks to capture it
- parsing daily-note schedule and reminder intent: automatic for `Sync today`
- completing, deleting, reprioritizing, assigning dates, changing recurrence,
  or moving tasks: explicit user intent required
- bulk changes, commitment writes, calendar writes, and external reminders:
  preview and confirm first; an explicitly authorized scheduled sync may reuse
  that authorization for unchanged managed entries
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
Never create calendar events or reminders from task-query results or arbitrary
daily-note prose. Invalid sync entries produce a no-write parse report.
