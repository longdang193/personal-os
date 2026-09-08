---
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: completed
layer: change
name: ssot-daily-planner
targets:
  - .agents/skills/skill-daily-planner/SKILL.md
  - docs/operating_system/procedures/daily-planner.md
  - tests/test_daily_planner_skill.py
  - generated_runtime/openclaw/skills/skill-daily-planner/SKILL.md
---

# SSOT Daily Planner Skill

## Goal

Create one runtime-neutral Daily Planner skill for Nanobot, OpenClaw, and
Hermes. Obsidian Markdown remains the only durable task and planning state.
Nanobot remains an edge relay in this repository; planner requests route to
Personal CoS instead of adding personal tools to the relay surface.

## Implementation Outcomes

### Portable planner contract

Add `.agents/skills/skill-daily-planner/SKILL.md` as canonical behavior source.
Keep frontmatter and instructions compatible with all three loaders. Use
capability-neutral operations, not runtime commands, provider APIs, or a second
planner database.

The skill owns:

- `plan today`, `plan tomorrow`, `plan review`, and `capture` behavior
- Markdown task syntax and source-note ownership
- daily-note managed-section boundaries
- preview, confirmation, idempotency, and ambiguity rules
- calendar and reminder authorization

### Obsidian SSOT

Use runtime-local `OBSIDIAN_VAULT_ROOT` outside Git. Use relative paths:

- `Planner/Inbox.md` for uncategorized capture
- `Planner/Commitments.md` for externally promised work
- `Daily/YYYY-MM-DD.md` for schedule, review, and planning snapshots
- existing project notes for project-owned tasks

Do not store planner state under `~/planner/`, runtime memory, or a task
database. Daily notes may contain snapshots, but task completion and
rescheduling always update source Markdown tasks.

### Runtime boundaries

- OpenClaw receives generated skill output through existing generator.
- Nanobot stays relay-only and forwards planner requests to Personal CoS.
- Hermes consumes the same single-file skill through its supported skill path.
- No Hermes adapter or new Nanobot tool surface is added in this plan.

### Proof and procedure

Add skill contract tests, generated-surface validation, operational setup
procedure, and compatibility smoke instructions. Preserve unrelated working
tree changes in `scripts/personal_cos_launcher.py` and
`tests/test_personal_cos_launcher.py`.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Default task executor: `codex`
- Required skills: `skill-central-config-layer`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit canonical skill/docs/tests, regenerate declared OpenClaw output, and run declared local checks
- User-approval actions: install or authenticate external runtimes, write to real Obsidian vault, change runtime configuration outside this repository, commit, push, or delete data
- Parallel ownership: none
- Sequential fallback: complete Task 0 before editing skill; stop if direct Nanobot execution is required or capability names cannot map without changing relay boundary

## Task Breakdown

### Task 0: Lock planner contract and capability boundary

**Purpose:**
- Turn SSOT intent into exact task, file, write, scheduling, and runtime rules.

**Task Function:**
- Contract reconciliation.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: repository truth and boundary decisions are locally inspectable.

**Specification Coverage:**
- One SSOT, runtime portability, Nanobot relay preservation, safe writes, and low-maintenance scope.

**Required Skills:**
- `skill-central-config-layer`

**Files And Symbols:**
- Inspect: `README.md`, `repo_config/runtime_surface_manifest.json`, `repo_config/tool_registry.toml`, `adapters/nanobot/manifest.toml`, `scripts/generate_runtime_surface.py:adapter_output_files`, `.agents/skills/skill-knowledge-search/SKILL.md`, `.agents/skills/skill-calendar-management/SKILL.md`
- Modify: none
- Verify: this plan

**Dependencies:**
- Existing Personal OS source and Nanobot relay contract.

**Authority:**
- Preauthorized local actions: read tracked source and record contract decisions in this plan
- Stop for: request to make Nanobot direct personal-tool runtime, add second task store, or place real vault path or credential in Git

**Steps:**
- [x] Define task line contract: Markdown checkbox, ISO due date, optional recurrence, optional priority, source-note ownership.
- [x] Define daily-note markers; planner replaces only its managed section and preserves user content.
- [x] Define commands: planning writes managed daily section; capture appends Inbox; completion, deadline changes, commitment writes, calendar writes, and bulk moves require explicit intent or confirmation.
- [x] Define unavailable-capability behavior: return read-only plan and identify missing capability; never claim write.
- [x] Record direct Nanobot execution as out of scope; relay invocation remains supported.

**Verification:**
- [x] Inspect plan for one owner per fact and no unresolved runtime command requirement.
- Expected: implementation needs no database, adapter protocol, or provider API.

**Exit Criteria:**
- Contract decisions are explicit and align with generated-surface ownership.

### Task 1: Implement canonical portable skill

**Purpose:**
- Add one audited skill that plans against Obsidian Markdown without duplicating durable state.

**Task Function:**
- Skill authoring and safety-boundary implementation.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: single-file policy work after Task 0 contract lock.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: focused tests and final verification cover this file.

**Specification Coverage:**
- Portable loading, Obsidian SSOT, task syntax, managed writes, planning workflow, confirmations, idempotency, failure reporting.

**Required Skills:**
- `skill-central-config-layer`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `.agents/skills/skill-knowledge-search/SKILL.md`, `.agents/skills/skill-calendar-management/SKILL.md`, `.agents/skills/skill-personal-chief-of-staff/SKILL.md`
- Modify: `.agents/skills/skill-daily-planner/SKILL.md`
- Verify: `.agents/skills/skill-daily-planner/SKILL.md`

**Dependencies:**
- Task 0 complete.

**Authority:**
- Preauthorized local actions: create canonical skill with provider-neutral instructions and no real-vault writes
- Stop for: runtime-specific syntax in canonical skill, destructive task migration, or automatic external calendar/mail writes

**Steps:**
- [x] Add minimal frontmatter with `name: skill-daily-planner` and description.
- [x] Define neutral inputs: current date/timezone, vault root, open tasks, commitments, calendar events, capacity, and constraints.
- [x] Define outputs: Top 3, schedule blocks, conflicts, carry-forward, blocked items, and evening review.
- [x] Define Markdown task grammar and source-note rule; reject ambiguous duplicate matches.
- [x] Define managed daily markers and exact-dedupe Inbox append behavior.
- [x] Define write and confirmation policy, including no-write fallback.
- [x] Keep calendar read-only for planning; route reminders through runtime scheduler only when requested.
- [x] Exclude email extraction, automatic commitment inference, time tracking, background reconciliation, and alternate task databases.

**Verification:**
- [x] Read skill as Nanobot, OpenClaw, and Hermes loader input; no provider command or private path appears.
- [x] Confirm every write has explicit target, preservation rule, and failure report.
- Expected: one file describes complete planner behavior without one runtime's tool names.

**Exit Criteria:**
- Canonical skill is self-contained, portable, bounded, and safe to project.

### Task 2: Document runtime installation and vault setup

**Purpose:**
- Give operators one setup procedure without duplicating planner policy.

**Task Function:**
- Operational documentation.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: documentation follows canonical skill and existing procedures.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: procedure is checked against repository commands and generated outputs.

**Specification Coverage:**
- Nanobot relay use, OpenClaw projection, Hermes single-file compatibility, private vault configuration, rollback.

**Required Skills:**
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `README.md:Generate`, `scripts/generate_runtime_surface.py:main`, `scripts/start_nanobot.ps1`, `docs/operating_system/procedures/knowledge-search.md`, `generated_runtime/nanobot/AGENTS.md`, `generated_runtime/openclaw/AGENTS.md`
- Modify: `docs/operating_system/procedures/daily-planner.md`
- Verify: `docs/operating_system/procedures/daily-planner.md`

**Dependencies:**
- Task 1 complete.

**Authority:**
- Preauthorized local actions: update tracked documentation and use fake/example paths
- Stop for: instruction to record real vault path, credential, session, or scheduler state in repository

**Steps:**
- [x] Document `OBSIDIAN_VAULT_ROOT` as runtime-local configuration outside Git.
- [x] Document minimal vault layout and task examples; state source-note ownership.
- [x] Document `python scripts/generate_runtime_surface.py` and `--check` for OpenClaw projection.
- [x] Document Nanobot planner flow as relay request to Personal CoS; do not install planner tools into generated edge surface.
- [x] Document Hermes installation from canonical `SKILL.md` and required file/calendar/scheduler capabilities.
- [x] Document seven-day pilot, failure handling, and rollback by removing skill and managed sections; no bulk migration.

**Verification:**
- [x] Check every command exists or is explicitly labeled external-runtime setup.
- [x] Confirm procedure contains no private data or duplicated policy.
- Expected: one vault works across three runtimes without another SSOT.

**Exit Criteria:**
- Procedure is actionable and clear about Nanobot relay limits.

### Task 3: Add focused tests and refresh projection

**Purpose:**
- Prove skill shape, SSOT invariants, generated OpenClaw projection, and relay boundary preservation.

**Task Function:**
- Regression-test authoring and generated-surface reconciliation.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: small Python unittest coverage matches repository style.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: final verification owns independent repository checks.

**Specification Coverage:**
- Frontmatter, portable wording, SSOT safety, generated output, Nanobot boundary.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `tests/test_validate_repo_contracts.py:ValidateRepoContractsTests`, `scripts/generate_runtime_surface.py:sync_repo`, `scripts/validate_repo_contracts.py:skill_issues`
- Modify: `tests/test_daily_planner_skill.py`
- Generate: `generated_runtime/openclaw/skills/skill-daily-planner/SKILL.md`
- Verify: `generated_runtime/openclaw/skills/skill-daily-planner/SKILL.md`, `generated_runtime/nanobot/`

**Dependencies:**
- Tasks 1 and 2 complete.

**Authority:**
- Preauthorized local actions: add focused tests and run generator for canonical inputs
- Stop for: generated Nanobot skill output, unrelated generated drift, or real credentials required

**Steps:**
- [x] Test required frontmatter and required planner sections.
- [x] Test Markdown task syntax, source-note ownership, managed-section preservation, confirmation, fallback.
- [x] Test absence of `~/planner/`, provider install commands, credentials, and real vault paths.
- [x] Run generator and confirm OpenClaw projection equals source.
- [x] Confirm Nanobot generated surface remains relay-only.

**Verification:**
- [x] `python -m unittest tests.test_daily_planner_skill tests.test_validate_repo_contracts`
- Expected: focused tests pass; OpenClaw output equals source; Nanobot output does not gain planner skill.

**Exit Criteria:**
- Tests fail on SSOT drift, unsafe writes, non-portable commands, stale projection, or relay expansion.

### Task 4: Run integration smoke and reconcile

**Purpose:**
- Prove representative planner flows and leave repository ready for approval.

**Task Function:**
- Acceptance verification.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: final proof spans source, generated output, tests, and runtime boundaries.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: `skill-verification-before-completion` owns final proof.

**Specification Coverage:**
- Direct planner behavior, relay behavior, no-write failure, idempotency, generated consistency.

**Required Skills:**
- `skill-backend-verification`
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: all plan targets, `scripts/personal_edge_adapter.py:handle`, `tests/test_personal_edge_adapter.py`
- Modify: none unless declared drift is found
- Verify: all plan targets and working tree

**Dependencies:**
- Task 3 complete.

**Authority:**
- Preauthorized local actions: run local tests, generator checks, contract validation, and fake-vault smoke checks
- Stop for: real-vault write, external authentication, failed proof, stale generated output, or unrelated working-tree conflict

**Steps:**
- [x] Run fake-vault smoke: capture, plan, repeat plan, ambiguous match, unavailable vault, managed-section preservation.
- [x] Run Nanobot relay smoke through existing local boundary; confirm no local task mutation.
- [x] If Hermes is installed and user authorizes runtime smoke, verify discovery of same `SKILL.md`; otherwise record static proof and defer runtime smoke.
- [x] Run final checks and inspect diff for unrelated modifications.
- [x] Record smoke deferrals or capability mismatches in this plan.

**Verification:**
- [x] `python -m unittest discover -s tests -p "test_*.py"`
- [x] `python scripts/generate_runtime_surface.py --check`
- [x] `python scripts/validate_repo_contracts.py`
- Expected: checks pass; fake-vault and relay flows show correct state and side effects; no private data or generated drift enters Git.

**Exit Criteria:**
- Evidence supports implementation approval; plan status changes to `completed` only after fresh completion verification returns `verified`.

**Recorded Result (2026-09-08):**
- Canonical skill, procedure, focused tests, generated OpenClaw projection, and relay-boundary checks completed.
- `python -m unittest tests.test_daily_planner_skill tests.test_validate_repo_contracts` passed: 18 tests.
- `python -m unittest discover -s tests -p "test_*.py"` passed: 53 tests.
- `python scripts/generate_runtime_surface.py --check` and `python scripts/validate_repo_contracts.py` passed.
- Hermes live discovery deferred; no Hermes runtime or authentication used. Static compatibility proof uses portable frontmatter and runtime-neutral skill instructions.

## Verification

- `python -m unittest tests.test_daily_planner_skill tests.test_validate_repo_contracts`
- `python -m unittest discover -s tests -p "test_*.py"`
- `python scripts/generate_runtime_surface.py --check`
- `python scripts/validate_repo_contracts.py`
- Fake-vault boundary proof for capture, plan, repeat plan, ambiguous match, unavailable capability, and managed-section preservation.
- Nanobot relay proof showing forwarding without local planner tools or state.
- Optional authorized Hermes discovery proof using same canonical `SKILL.md`.

## Completion Criteria

1. `.agents/skills/skill-daily-planner/SKILL.md` is the only planner behavior source.
2. Obsidian Markdown is the only durable task and planning state; no `~/planner/`, runtime memory, or task database is added.
3. OpenClaw projection is generated and current.
4. Nanobot remains relay-only and supports planner requests through Personal CoS.
5. Hermes consumes the same single-file skill without runtime-specific policy text.
6. Writes preserve user-authored vault content, use explicit targets, and report failure without claiming success.
7. Task, calendar, reminder, and bulk-mutation authorization rules are tested or smoke-proven.
8. Procedures contain no private vault path, credential, session, or scheduler state.
9. Existing unrelated working-tree changes remain untouched.
10. Final verification passes with evidence recorded before plan status changes from `proposed`.
