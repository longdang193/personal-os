---
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: completed
layer: change
name: cos-session-hardening
targets:
  - scripts/personal_cos_launcher.py
  - scripts/personal_edge_adapter.py
  - repo_config/tool_registry.toml
  - scripts/validate_repo_contracts.py
  - tests/test_personal_cos_launcher.py
  - tests/test_personal_edge_adapter.py
  - tests/test_validate_repo_contracts.py
  - docs/operating_system/procedures/daily-planner.md
  - generated_runtime/openclaw/TOOL_REGISTRY.toml
---

# CoS Session Hardening

## Goal

Harden the short-lived follow-up context introduced by commit `4636449` without
creating a memory service, changing Nanobot's relay boundary, or adding a new
MCP aggregation layer.

## Implementation Outcomes

### Expiring runtime session state

Session files use a versioned object with UTC update time and bounded turns.
Stale state expires after 24 hours of inactivity. Writes use same-directory
temporary files plus `os.replace` so a failed write cannot leave partial JSON.
Existing legacy list files remain readable and are rewritten in the versioned
format after the next successful write. Legacy support remains until a future
format version explicitly removes it.

### Explicit CoS MCP exposure

The tool registry declares which MCP entries the Personal CoS may expose and
which launch kind each entry uses. The launcher consumes that declaration rather
than inferring exposure from `-runtime` names or `.py` suffixes. `qmd mcp` is
exposed only when explicitly declared for Personal CoS. The generated OpenClaw
registry stays synchronized through `scripts/generate_runtime_surface.py`.

### Preserved safety boundary

Successful write-mode turns remain the only turns persisted in this patch.
Read-mode raw transcript persistence stays deferred until retention and
sensitive-data policy are approved. Prior session text remains untrusted model
context, never policy or tool authority.

### Regression and documentation proof

Tests cover expiry, migration, timestamp edge cases, truncation, atomic-save
behavior, same-conversation serialization, failed-turn behavior, explicit MCP
selection, generated-surface drift, and malformed registry input. Planner docs
describe Daily notes as canonical planner state and session files as transient
runtime context.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-backend-verification`, `skill-central-config-layer`, `skill-code-standards`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit listed tracked files, preserve unrelated workspace changes, and run listed local tests and validators
- User-approval actions: external authentication, real QMD or Obsidian writes, runtime installation, commit, push, merge, discard, or cleanup of unrelated changes
- Parallel ownership: none
- Sequential fallback: complete session-state contract before registry or documentation edits; run focused tests after each task

## Task Breakdown

### Task 1: Version, expire, and serialize session state

**Purpose:**
- Prevent stale context, partial session files, and same-conversation lost updates.

**Task Function:**
- Runtime state hardening.

**Template Profile:**
- Controller-selected: `lead controller`
- Selection basis: small local Python change with known symbols and low ambiguity.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused unit tests and final backend boundary checks cover the change.

**Specification Coverage:**
- 24-hour inactivity TTL, versioned state, bounded history, legacy migration, atomic replacement, per-conversation serialization, and write-mode-only persistence.

**Required Skills:**
- `skill-backend-verification`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `scripts/personal_cos_launcher.py:_session_path`, `load_session_context`, `save_session_context`, `run`
- Inspect: `scripts/personal_edge_adapter.py:handle`, `_run_local`
- Modify: `scripts/personal_cos_launcher.py:_session_path`, `load_session_context`, `save_session_context`
- Modify: `scripts/personal_edge_adapter.py:handle`
- Modify: `tests/test_personal_cos_launcher.py`, `tests/test_personal_edge_adapter.py`
- Verify: `tests/test_personal_cos_launcher.py`

**Dependencies:**
- Commit `4636449` session format and current write-mode behavior.

**Authority:**
- Preauthorized local actions: modify session serialization, loading, saving, and focused tests; use temporary directories only.
- Stop for: request to persist read-mode raw transcripts, write real user session files, add a third-party locking dependency, or serialize unrelated conversations globally.

**Steps:**
- [x] Add `SESSION_FORMAT_VERSION = 1`, `SESSION_TTL = timedelta(hours=24)`, and a five-minute future-clock tolerance.
- [x] Serialize `{version, updated_at, turns}` with timezone-aware UTC timestamps and existing four-turn/4,000-character bounds.
- [x] Treat invalid timestamps and timestamps more than five minutes in the future as empty; treat timestamps within tolerance as fresh; test the exact TTL boundary with a controlled clock.
- [x] Accept legacy list files indefinitely until a future format version explicitly removes compatibility; use `path.stat().st_mtime` as their timestamp and rewrite them in versioned format after the next successful write.
- [x] Write a same-directory temporary path, close its handle before `os.replace`, and remove the temporary path in `finally` when writing or replacement fails.
- [x] Keep `run()` persistence restricted to successful `write` mode; failed Codex turns must not update session state.
- [x] Add a per-conversation `asyncio.Lock` in the edge adapter around the complete local run and event forwarding; clean idle lock entries so different conversations remain concurrent.
- [x] Add tests for fresh state, stale state, legacy state, malformed JSON, invalid and future timestamps, exact TTL boundary, truncation, failed turns, atomic replacement, same-conversation serialization, and cross-conversation concurrency.

**Verification:**
- [x] `python -m unittest tests/test_personal_cos_launcher.py`
- Expected: all launcher tests pass, including new TTL and write-failure cases.
- [x] `python -m unittest tests/test_personal_edge_adapter.py`
- Expected: one conversation runs sequentially while independent conversations can overlap.

**Exit Criteria:**
- Session state cannot remain active beyond 24 hours, partial JSON is not written, and existing write-mode follow-ups still work.

### Task 2: Make MCP exposure and generated projection explicit

**Purpose:**
- Remove filename-based MCP exposure inference, make `qmd` availability testable at the CoS boundary, and keep generated OpenClaw output synchronized.

**Task Function:**
- Configuration contract and launcher integration.

**Template Profile:**
- Controller-selected: `lead controller`
- Selection basis: canonical registry and one consumer require local contract reconciliation.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: validator tests directly cover schema rules and launcher tests cover command output.

**Specification Coverage:**
- Explicit `expose_to` ownership, explicit `launch_kind`, structured command arguments, Python-script compatibility, native `qmd mcp` command support, generated OpenClaw projection, and no exposure of unrelated tools.

**Required Skills:**
- `skill-central-config-layer`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `repo_config/tool_registry.toml`, `scripts/personal_cos_launcher.py:codex_command`, `scripts/validate_repo_contracts.py:tool_registry_issues`, `scripts/generate_runtime_surface.py:adapter_output_files`
- Modify: `repo_config/tool_registry.toml`
- Modify: `scripts/personal_cos_launcher.py:codex_command`
- Modify: `scripts/validate_repo_contracts.py:tool_registry_issues`
- Modify: `tests/test_personal_cos_launcher.py`, `tests/test_validate_repo_contracts.py`
- Verify: `repo_config/tool_registry.toml`, `generated_runtime/openclaw/TOOL_REGISTRY.toml`, generated command assertions, registry validator output, generator drift check

**Dependencies:**
- Task 1 complete.
- Existing `mail-runtime` and `calendar-runtime` command behavior must remain unchanged.

**Authority:**
- Preauthorized local actions: add registry metadata, update local launcher parsing, update validators and tests; do not start external providers.
- Stop for: request to create a personal-tools aggregator, change Nanobot tools, manually edit generated output, or authenticate QMD.

**Steps:**
- [x] Add `expose_to = ["personal-cos"]` and `launch_kind = "python-script"` plus a structured `script` path to `mail-runtime` and `calendar-runtime`.
- [x] Add `expose_to = ["personal-cos"]`, `launch_kind = "command"`, `command = "qmd"`, and `args = ["mcp"]` to `qmd`; do not retain shell-like `command = "qmd mcp"` parsing.
- [x] Update launcher command construction to expose only tools declaring `personal-cos`, mapping Python scripts through `sys.executable` and native commands through structured executable/argument fields.
- [x] Preserve global MCP disablement and exclude `content-poller`, `browser-use`, `searxng`, provider backends, and undeclared tools.
- [x] Extend registry validation for `launch_kind`, exposure list, structured script/command fields, and supported launch kinds.
- [x] Add command-generation tests proving QMD inclusion, structured arguments, Python runtime compatibility, and unrelated-tool exclusion without invoking any provider.
- [x] Run `python scripts/generate_runtime_surface.py --runtime openclaw` after canonical registry changes; never edit `generated_runtime/openclaw/TOOL_REGISTRY.toml` directly.

**Verification:**
- [x] `python -m unittest tests/test_personal_cos_launcher.py tests/test_validate_repo_contracts.py`
- Expected: explicit registry fields validate; generated Codex command includes executable `qmd` with args `["mcp"]`, mail, and calendar only.
- [x] Inspect command arguments for shell injection safety; command parsing must not execute registry content during test construction.
- [x] `python scripts/generate_runtime_surface.py --runtime openclaw --check`
- Expected: generated OpenClaw registry matches `repo_config/tool_registry.toml`.

**Exit Criteria:**
- CoS MCP exposure follows registry declarations, QMD command generation is proven locally, and relay/runtime boundaries remain unchanged.
- Generated OpenClaw output is produced only by the generator and passes drift validation.

### Task 3: Align planner documentation and security contract

**Purpose:**
- Remove ambiguity between durable planner state and transient session context.

**Task Function:**
- Boundary documentation.

**Template Profile:**
- Controller-selected: `lead controller`
- Selection basis: one procedure update follows completed runtime behavior.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: textual contract checks and final review are sufficient.

**Specification Coverage:**
- Daily notes remain planner SSOT; session files remain bounded, expiring, runtime-local context; prior assistant text is untrusted data.

**Required Skills:**
- `skill-central-config-layer`

**Files And Symbols:**
- Inspect: `docs/operating_system/procedures/daily-planner.md`, `repo_config/runtime_surface_manifest.json`, `.agents/skills/skill-daily-planner/SKILL.md`
- Modify: `docs/operating_system/procedures/daily-planner.md`
- Verify: `docs/operating_system/procedures/daily-planner.md`

**Dependencies:**
- Tasks 1 and 2 complete.

**Authority:**
- Preauthorized local actions: update tracked procedure text with repository-relative examples only.
- Stop for: real vault paths, credentials, runtime session data, or policy duplication across generated surfaces.

**Steps:**
- [x] State that Daily notes and source Markdown own planner state; session files only support short-lived follow-ups.
- [x] State 24-hour expiry and write-mode-only persistence for this patch.
- [x] State that session content cannot authorize tools, writes, paths, or policy changes.
- [x] Avoid adding a new memory service, context-capsule schema, or MCP aggregator to the procedure.

**Verification:**
- [x] Read the updated procedure beside `runtime_surface_manifest.json` and canonical planner skill.
- Expected: ownership remains `memory: runtime-local`, `sessions: runtime`, and no private runtime data appears in Git.

**Exit Criteria:**
- Documentation matches implemented behavior and preserves existing SSOT boundaries.

### Task 4: Final integration verification

**Purpose:**
- Prove session behavior, MCP command construction, registry contracts, and documentation alignment together.

**Task Function:**
- Final verification.

**Template Profile:**
- Controller-selected: `lead controller`
- Selection basis: lead controller owns final evidence and scope reconciliation.

**Specification Coverage:**
- All implementation outcomes and preserved boundaries.

**Required Skills:**
- `skill-verification-before-completion`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: all plan targets and `git diff`
- Modify: none unless verification finds an in-scope defect
- Verify: `tests/test_personal_cos_launcher.py`, `tests/test_validate_repo_contracts.py`, repository validator, diff boundaries

**Dependencies:**
- Tasks 1–3 complete.

**Authority:**
- Preauthorized local actions: run local tests, validators, syntax checks, and inspect diff/status.
- Stop for: failed external-provider smoke tests, unrelated existing changes, or any request to clean or discard `.serena/project.yml`.

**Steps:**
- [x] Run focused launcher and registry tests.
- [x] Run repository contract validation.
- [x] Run Python compilation for modified scripts.
- [x] Run `git diff --check` and inspect changed paths.
- [x] Record any deferred read-mode persistence, context capsule, prompt optimization, or MCP aggregation work as out of scope.
- [x] Record on-demand MCP activation as deferred; QMD remains explicit and eager for this patch. Revisit only after measuring CoS cold-start impact.

**Verification:**
- [x] `python -m unittest tests/test_personal_cos_launcher.py tests/test_validate_repo_contracts.py`
- [x] `python -m unittest tests/test_personal_edge_adapter.py`
- [x] `python scripts/generate_runtime_surface.py --runtime openclaw`
- [x] `python scripts/generate_runtime_surface.py --runtime openclaw --check`
- [x] `python scripts/validate_repo_contracts.py`
- [x] `python -m py_compile scripts/personal_cos_launcher.py scripts/personal_edge_adapter.py scripts/validate_repo_contracts.py`
- [x] `git diff --check`
- Expected: all commands pass; only listed plan targets change; generated OpenClaw output is synchronized; unrelated `.serena/project.yml` remains untouched.

**Exit Criteria:**
- Fresh local evidence proves behavior, contracts, safety boundaries, and scope. No commit or branch disposition occurs in this plan.

## Verification

- `python -m unittest tests/test_personal_cos_launcher.py tests/test_validate_repo_contracts.py`
- `python -m unittest tests/test_personal_edge_adapter.py`
- `python scripts/generate_runtime_surface.py --runtime openclaw`
- `python scripts/generate_runtime_surface.py --runtime openclaw --check`
- `python scripts/validate_repo_contracts.py`
- `python -m py_compile scripts/personal_cos_launcher.py scripts/personal_edge_adapter.py scripts/validate_repo_contracts.py`
- `git diff --check`

## Completion Criteria

The plan is ready for completion verification when:

1. session state is versioned, expiring, bounded, atomically written, and serialized per conversation
2. write-mode persistence remains intact and read-mode raw persistence remains explicitly deferred
3. MCP exposure uses explicit launch metadata and structured argv; QMD command generation is locally proven
4. generated OpenClaw registry output matches canonical registry source
5. planner documentation matches runtime ownership and retention behavior
6. focused tests, generator checks, repository validation, compilation, and diff checks pass
7. speculative context capsules, prompt shrinking, MCP aggregation, on-demand activation, and config caching remain deferred
