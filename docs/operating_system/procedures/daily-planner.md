# Daily Planner

Daily Planner uses Obsidian Markdown as single source of truth. Runtime memory,
`~/planner/`, and separate task databases are not planner state.

## Vault Setup

Set `OBSIDIAN_VAULT` in each runtime's private local configuration. Do not
store real vault paths, credentials, sessions, or scheduler state in Git.

Create only these folders when they do not already exist:

```text
<vault>/Planner/Commitments.md
<vault>/Daily/
```

Keep project tasks in their existing project notes. Use Obsidian Tasks syntax:

```markdown
- [ ] Review German material 📅 2026-09-08 #area/german
- [ ] Submit application 📅 2026-09-12 ⏫
```

Relative dates are explicit input. On September 8, 2026, `Notify roommates;
complete today` is written as `- [ ] Notify roommates 📅 2026-09-08`.

Each calendar day has its own note named `YYYY-MM-DD.md` inside `Daily/`.
Source note owns task state. Daily notes contain schedule blocks and live
Obsidian Tasks queries, not copied task lines.

Daily notes also own external intent. Keep calendar and reminder entries inside
the managed block using these exact forms:

```markdown
### Schedule
- 2026-09-08 09:00–10:00 | Roommate meeting

### Reminders
- 2026-09-08 18:00 | Notify roommates
```

Google Calendar and the runtime scheduler receive projections from these lines;
they are not second sources of truth.

## Runtime Installation

Canonical source:

```text
.agents/skills/skill-daily-planner/SKILL.md
```

OpenClaw projection:

```powershell
python scripts/generate_runtime_surface.py
python scripts/generate_runtime_surface.py --check
python scripts/generate_runtime_surface.py --runtime openclaw --install-dir "$HOME/.openclaw/workspace"
```

Nanobot remains relay-only in this Personal OS repository. Send `Plan today`,
`Capture <task>`, or `Plan review` through Nanobot; Personal CoS performs the
planner operation. Do not add planner tools or private vault access to the
generated Nanobot edge surface. The local CoS launcher injects the canonical
daily-planner skill into each Codex turn; a skill path mention alone is not
enforcement.

Hermes uses the same canonical `SKILL.md` in its configured local skill
directory or supported repository installation path. Keep runtime installation
syntax outside the canonical skill. Hermes must provide file read/write access
to the configured vault; calendar and reminder capabilities remain optional.

## Commands

- `Plan today`: preview or save today's managed daily-plan block.
- `Plan tomorrow`: prepare next day's plan without automatic rescheduling.
- `Capture <task>`: append one deduplicated checkbox to current `Daily/YYYY-MM-DD.md`.
- `Plan review`: report completed, overdue, blocked, and carried-forward work.
- `Sync today`: preview and, after one confirmation, sync managed schedule
  entries to Google Calendar and reminder entries to the runtime scheduler.

Planner owns only this marker block in each daily note:

```markdown
<!-- daily-planner:managed:start -->
<!-- daily-planner:managed:end -->
```

The managed block must use Obsidian Tasks syntax and query blocks:

````markdown
### Top 3
```tasks
not done
due today
sort by priority
sort by due
limit 3
```
````

Query results remain linked to source Markdown tasks. Do not paste query results
back into daily notes as duplicate checkboxes.

`Sync today` reads only managed `Schedule` and `Reminders` sections. It uses
stored external IDs for idempotent updates, reports removed entries as
orphaned, and never cancels external projections without confirmation. Linkage
comments use `<!-- personal-os:calendar-id=ID -->` and
`<!-- personal-os:reminder-id=ID -->`; plan regeneration preserves matching
comments.

All content outside markers remains user-owned. Multiple marker pairs stop the
write and produce an ambiguity report.

## Safety

- Planning reads calendar; it does not create or move calendar events.
- `Sync today` may create or update explicit managed calendar entries after a
  single preview confirmation. It never infers events from prose or task
  query results.
- Completion, deletion, reprioritization, date changes, recurrence changes,
  bulk moves, commitment writes, and external reminders require explicit user
  intent; preview batch changes before confirmation.
- Missing vault, calendar, or scheduler capability produces a read-only result.
- Repeated planning for one date replaces one managed block and does not append
  duplicate plans.
- Never claim a write without result evidence.

## Seven-Day Pilot

Start with vault-only planning. Test capture, today's plan, repeat planning,
review, and carry-forward manually for seven days. Add calendar read access only
after Markdown writes remain stable. Add mail or automatic commitment
extraction only as separate approved work.

## Rollback

Disable or remove the runtime skill. Delete only the planner-owned marker block
from daily notes. Preserve all source tasks, user-authored note content, and
runtime memory.
