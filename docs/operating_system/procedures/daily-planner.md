# Daily Planner

Daily Planner uses Obsidian Markdown as single source of truth. Runtime memory,
`~/planner/`, and separate task databases are not planner state.

## Vault Setup

Set `OBSIDIAN_VAULT_ROOT` in each runtime's private local configuration. Do not
store real vault paths, credentials, sessions, or scheduler state in Git.

Create only these folders when they do not already exist:

```text
<vault>/Planner/Inbox.md
<vault>/Planner/Commitments.md
<vault>/Daily/
```

Keep project tasks in their existing project notes. Use Obsidian Tasks syntax:

```markdown
- [ ] Review German material 📅 2026-09-08 #area/german
- [ ] Submit application 📅 2026-09-12 ⏫
```

Source note owns task state. Daily notes contain planning snapshots and
schedule blocks, not authoritative duplicate tasks.

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
generated Nanobot edge surface.

Hermes uses the same canonical `SKILL.md` in its configured local skill
directory or supported repository installation path. Keep runtime installation
syntax outside the canonical skill. Hermes must provide file read/write access
to the configured vault; calendar and reminder capabilities remain optional.

## Commands

- `Plan today`: preview or save today's managed daily-plan block.
- `Plan tomorrow`: prepare next day's plan without automatic rescheduling.
- `Capture <task>`: append one deduplicated checkbox to `Planner/Inbox.md`.
- `Plan review`: report completed, overdue, blocked, and carried-forward work.

Planner owns only this marker block in each daily note:

```markdown
<!-- daily-planner:managed:start -->
<!-- daily-planner:managed:end -->
```

All content outside markers remains user-owned. Multiple marker pairs stop the
write and produce an ambiguity report.

## Safety

- Planning reads calendar; it does not create or move calendar events.
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
