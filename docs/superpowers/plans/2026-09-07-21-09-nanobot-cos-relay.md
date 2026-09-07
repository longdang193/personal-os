---
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: active
layer: change
name: nanobot-cos-relay
targets:
  - repo_config/frontend_registry.toml
  - repo_config/project_registry.toml
  - scripts/personal_edge_adapter.py
  - scripts/personal_cos_launcher.py
  - scripts/generate_runtime_surface.py
  - scripts/start_nanobot.ps1
  - tests/
  - docs/operating_system/
---

# Nanobot as Personal CoS Edge Relay

## Goal

Make Nanobot a Telegram-only edge for user-invoked Personal CoS. Nanobot
forwards owner messages and commands to a fresh explicit Personal CoS turn,
displays typed CoS events, and performs no memory lookup, agent selection, task
orchestration, repository access, or personal-domain action.

Personal CoS owns personal prioritization, memory, approvals, aggregation, and
personal task state. It invokes one local CoS runner with the selected repository
as working directory. The runner owns Project OS handoff and Herdr activation.
Project OS owns canonical work truth, execution policy, executor/profile/worktree
selection, Project CoS activation, Herdr lane selection, lane briefing, evidence
reconciliation, retirement, and execution proof. MAIN AGENTS own lane execution.

## Implementation Outcomes

### One canonical relay contract

Keep one provider-neutral `personal.edge.v1` JSON envelope and reuse existing
`personal.dispatch.v1` for Personal CoS to Project OS handoff. Use local process
transport: Nanobot invokes Codex CLI through one runner, with the selected
repository as `--cd`; no URL or auth token exists. Keep configuration
SSOT split by responsibility: `frontend_registry.toml` owns frontend roles and
edge settings; `project_registry.toml` owns repository IDs and roots. Generated
runtime surfaces consume both; Nanobot and future frontends copy neither policy
nor transport settings.

### Validated repository targeting

Add one project registry mapping canonical repository IDs to local environment
roots. Nanobot transports optional `repository_id`, `repository_ref`, and
`access_mode` as opaque request metadata; Personal CoS forwards them through
`personal.dispatch.v1`; Project OS validates them. Absolute paths never enter
the edge or dispatch contract.

### Deterministic Nanobot boundary

Nanobot uses a relay adapter or supported channel hook that forwards raw
messages and commands without model-mediated delegation. Local task tools,
agent routing, and decision-making are disabled.

### Typed progress delivery

The local runner emits ordered `personal.event.v1` JSONL events with
`request_id`, `sequence`, `type`, and `payload`. The edge renders events for
Telegram without adding a task database, event broker, HTTP server, or
persistent CoS session. Herdr remains inside Project OS and is not a Personal OS
transport dependency.

### Symmetric frontend onboarding

All frontends use the same request, command, event, retry, and authorization
contract. Adding a bot requires one configuration entry and one runtime syntax
adapter, not new orchestration logic.

### Proof and documentation

Contract tests, Nanobot capability-gate tests, generated-surface validation,
Project OS handoff proof, and a Telegram smoke procedure prove forwarding,
progress, status recovery, approval, cancellation, and tool isolation.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Default task executor: `codex`
- Required skills: `skill-central-config-layer`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit tracked source, tests, canonical documentation, generated projections, and local Nanobot configuration; run declared local checks
- User-approval actions: commit, push, Telegram writes beyond smoke testing, credential changes, destructive cleanup, and changes outside this repository
- Parallel ownership: none
- Sequential fallback: complete Task 0 first; stop all implementation if Nanobot lacks a deterministic pre-agent ingress path

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `master`
- Base commit: `4bc0a2f`
- Expected workspace: implementation changes present in current workspace; preserve unrelated changes
- Next action: `Task 4 — complete authorized Telegram smoke, then obtain Project OS acceptance evidence`
- Blockers: `live Telegram smoke and repository-scoped CoS/Project OS acceptance remain later gates`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 0 | `done` | current | `codex` | none | Nanobot capability proof | pinned patches and disposable ingress proof recorded below |
| Task 1 | `done` | current | `codex` | Task 0 | local-process SSOT tests | focused contract and validator checks pass |
| Task 2 | `done` | current | `codex` | Task 1 | local runner boundary tests | focused adapter/launcher tests and real `codex exec --json --cd` smoke pass |
| Task 3 | `done` | current | `codex` | Task 1 | generated surfaces and validators | relay projection remains valid |
| Task 4 | `pending` | current | `codex` | Tasks 0, 2–3 | Nanobot edge-relay runtime proof | local hook/config proof passed; live Telegram smoke pending |
| Task 5 | `blocked` | current | `codex` | Tasks 2–4 | Project OS handoff proof | Project OS public boundary not available in this repository |
| Task 6 | `blocked` | current | `codex` | Tasks 0–5 | fresh final verification | depends on Task 5 and Telegram smoke |

## Scope And Decisions

- Herdr is Project OS internal infrastructure. Personal OS does not connect to,
  wrap, or expose Herdr.
- Do not add a custom HTTP server, SSE broker, queue, task database, or event
  database for this relay.
- Project OS owns Herdr endpoint discovery, credentials, lane state, and
  execution observation; those are external integration evidence for this plan.
- Treat the active plan/task ledger as durable coordinated-work state. Treat
  Herdr output as pull-based, transient observation until CoS records
  structured acceptance evidence.
- Treat duplicate `request_id` as idempotent; never create duplicate tasks.
- Forward raw command text to CoS. Nanobot does not interpret `/status`,
  `/cancel`, `/approve`, or future commands.
- Keep Nanobot and CoS memory stores separate. CoS memory alone informs task
  decisions.
- Do not use bot-to-bot Telegram messages, prompt-only enforcement, direct
  Nanobot-to-Herdr access, or an MCP forwarding tool as the security boundary.
- Do not implement lane-execution mechanics in this repository. Personal CoS
  never selects Project OS plans, executors, profiles, worktrees, branches, or
  Herdr lanes. Project OS's repository-owned `skill-chief-of-staff` owns those
  decisions and lane execution.
- Repository access means forwarding canonical `repository_id`, optional
  `repository_ref`, and `access_mode`; Nanobot never receives arbitrary path,
  Git, or shell access.
- Store repository roots as local environment references in the registry; keep
  machine-specific absolute paths in `.env`, outside Git.
- The target Project OS public entrypoint rejects unknown IDs, path traversal,
  UNC paths, symlink/reparse escapes, unapproved refs, and unauthorized writes
  before execution.
- Configuration ownership is explicit: `personal_agent.toml` owns identity,
  `tool_registry.toml` owns capabilities, `frontend_registry.toml` owns edge
  protocol and frontend settings, and `project_registry.toml` owns repository
  mapping.
- `personal.edge.v1`, existing `personal.dispatch.v1`, and `personal.event.v1`
  use typed payloads only. No adapter infers state from free-form terminal text.
- Telegram owner identity binds to the relay request; bot-token possession
  alone does not authorize arbitrary users or commands.

## Preconditions And Stop Conditions

- Use the user-callable native Codex lead entrypoint with
  `C:\Users\HOANG PHI LONG DANG\.agents\skills\skill-chief-of-staff\SKILL.md`;
  no separate CoS repository is required for this plan.
- Prove a deterministic Nanobot channel hook and effective capability-deny
  mechanism before changing Nanobot runtime behavior.
- Project OS must prove its own Herdr boundary and typed observation schema
  before Task 5 is accepted. Personal OS does not implement that adapter.
- Prove the target Project OS public entrypoint and its repository validation
  contract before any repository read/write smoke test.
- Keep Personal CoS routing and Project OS CoS coordination distinct. Nanobot
  may forward to the user-invoked Personal CoS entrypoint, but Personal CoS
  cannot select Project OS execution lanes and Nanobot cannot activate agents.
- Stop execution when any precondition is missing. Keep the plan `proposed` or
  mark the affected task `blocked`; do not claim end-to-end completion.

## Task Breakdown

### Task 0: Prove Nanobot relay feasibility

**Purpose:**
- Prove a non-agent Telegram ingress path before changing runtime behavior.

**Task Function:**
- Runtime capability spike.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: capability gate prevents building an unsupported integration.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: direct installed-runtime inspection.

**Specification Coverage:**
- Nanobot must forward before its MessageBus/agent path and must not rely on prompt-only enforcement.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: installed Nanobot Telegram channel package, `_handle_message(...)`, plugin/channel commands
- Modify: none; record capability result in this plan
- Verify: installed package/version and one disposable pre-agent ingress probe

**Dependencies:**
- None.

**Authority:**
- Preauthorized local actions: inspect installed Nanobot source and run disposable local capability probes.
- Stop for: no supported pre-agent hook, channel replacement, or explicitly approved tiny pinned channel patch.

**Steps:**
- [x] Prove supported pre-agent Telegram interception hook.
- [x] If absent, prove supported channel replacement/override.
- [x] If absent, present tiny pinned `TelegramChannel` patch for explicit approval; do not implement silently.
- [x] Record exact version, hook location, capability-deny mechanism, and evidence.

**Verification:**
- [x] Disposable probe proves inbound Telegram text bypasses Nanobot agent processing and reaches edge adapter.
- Expected: pinned mechanism exists and Tasks 1–4 may proceed.

**Exit Criteria:**
- Deterministic relay ingress is proven and its maintenance/upgrade impact is recorded.

**Recorded Result (2026-09-07):**
- Installed runtime: `nanobot v0.3.0` from the user-local `uv` tool environment.
- `nanobot plugins list` exposes channel packages, not a supported pre-agent
  interception hook; `nanobot.channels.registry` detects legacy
  `nanobot.channels` entry points but explicitly does not load them.
- Telegram registers `_forward_command` and `_on_message` as native handlers;
  both paths call `BaseChannel._handle_message`.
- `BaseChannel._handle_message` publishes the authorized message directly to
  `MessageBus.inbound`; agent hooks run later inside `AgentLoop`.
- Result: no supported channel replacement or pre-agent ingress was proven;
  approved pinned patches provide deterministic ingress for this installed
  version. Tasks 1–4 may proceed.
- Applied patch provenance: `patches/nanobot-v0.3.0/0001-pre-agent-hook.patch`
  and `patches/nanobot-v0.3.0/0002-telegram-command-hook.patch`. Disposable
  package backups were removed after provenance was recorded.

### Task 1: Lock frontend/project registry SSOT and contracts

**Purpose:**
- Define one machine-readable owner for edge transport, frontend roles, protocol
  versions, and canonical repository targeting.

**Task Function:**
- Configuration and contract definition.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: direct, low-risk repository configuration change.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: contract tests run by lead controller.

**Specification Coverage:**
- SSOT, symmetric transport contract, intentional authority split, minimum maintenance, provider-neutral `personal.edge.v1`.

**Required Skills:**
- `skill-central-config-layer`

**Files And Symbols:**
- Inspect: `repo_config/tool_registry.toml`, `repo_config/personal_agent.toml`
- Modify: `repo_config/frontend_registry.toml`, `repo_config/project_registry.toml`
- Verify: `tests/test_frontend_registry.py`, `tests/test_project_registry.py`

**Dependencies:**
- Current clean `master` at `4bc0a2f`.

**Authority:**
- Preauthorized local actions: create the canonical contract and focused tests; run unit tests.
- Stop for: any requirement to store credentials, choose a CoS executor, or alter primary-agent policy.

**Steps:**
- [x] Keep machine-readable `personal.edge.v1` JSON payload with field types, request identity, and command forwarding rules.
- [x] Reuse existing `personal.dispatch.v1` for Personal CoS to Project OS handoff; add only required repository intent fields.
- [x] Keep typed `personal.event.v1` response fixtures with event identity, sequence scope, replay/gap rules, and terminal states.
- [x] Keep one `[[frontends]]` entry per runtime with role and token environment reference.
- [x] Keep one `[[projects]]` registry entry per approved repository with `id`, `root_env`, and access modes.
- [x] Add local-process transport metadata; remove URL and auth-token fields.
- [x] Add validation for unique frontend/project IDs, local transport, secret-free config, owner identity binding, and valid environment references.
- [x] Leave filesystem containment, path safety, ref authorization, and write authorization to the local CoS runner and Project OS boundary.
- [x] Extend `scripts/validate_repo_contracts.py` to validate the local runner contract.

**Verification:**
- [x] `python -m unittest tests/test_frontend_registry.py`
- [x] `python scripts/validate_repo_contracts.py`
- Expected: valid config passes; duplicate IDs, unsupported roles/access modes, non-local transports, literal secrets, unbound owner identities, and invalid environment references fail.

**Exit Criteria:**
- Contract has one owner and tests reject unsafe or asymmetric configuration.

### Task 2: Add Personal CoS edge contract

**Purpose:**
- Provide one thin local adapter between Nanobot and a user-invoked Personal CoS
  turn through a local runner.

**Task Function:**
- Edge transport and Personal CoS contract integration.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: narrow adapter change with direct boundary proof.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: direct backend tests cover success and failure paths.

**Specification Coverage:**
- Forwarding, request identity, repository targeting, authorization, typed
  events, and failure reporting.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: Personal CoS routing rules, `repo_config/frontend_registry.toml`, `codex exec --help`
- Modify: `scripts/personal_edge_adapter.py`, `scripts/personal_cos_launcher.py`
- Verify: `tests/test_personal_edge_adapter.py`, `tests/test_personal_cos_launcher.py`

**Dependencies:**
- Task 1 contract and state names.

**Authority:**
- Preauthorized local actions: add the thin edge adapter and isolated contract tests.
- Stop for: direct Nanobot access to Project OS internals, persistent session state, external writes, or implementation of CoS routing in Nanobot.

**Steps:**
- [x] Create one fresh explicit Personal CoS turn per Telegram request; do not keep a persistent CoS session.
- [x] Forward raw text and commands through `personal.edge.v1` on stdin; the local runner invokes `codex exec --json --cd <registered-repo> -`.
- [x] Normalize only local runner `personal.event.v1` JSONL responses.
- [x] Preserve `repository_id`, `repository_ref`, and `access_mode`; resolve paths only inside the local runner.
- [x] Reconstruct `/status`, retry, approval, cancellation, and reconnect behavior from canonical Personal OS/Project OS state; do not introduce a task ledger, broker, or session manager.
- [x] Return explicit unavailable, timeout, unknown, blocked, and failed states; never infer completion, retry, or acceptance from missing or stale output.

**Verification:**
- [x] `python -m unittest tests/test_personal_edge_adapter.py tests/test_personal_cos_launcher.py`
- [x] Verify direct Codex CLI boundary with sanitized local fixtures; do not parse free-form terminal text.
- Expected: request identity survives local runner calls; typed JSONL events normalize correctly; no Nanobot tool or lane selection occurs.

**Recorded Result (2026-09-07):**
- Focused adapter/launcher tests pass.
- Real `personal-os` smoke emitted ordered `accepted`, `progress`, and
  `completed` `personal.event.v1` events; Codex CoS returned `READY`.
- Windows gateway reproduction found `personal_edge_adapter.py` iterating an
  `asyncio.StreamReader`, raising `TypeError` before Telegram delivery. The
  adapter now awaits `.read()` and splits JSONL output.
- No URL, auth token, HTTP server, persistent session manager, or Herdr call
  exists in the Nanobot-to-CoS path.

**Exit Criteria:**
- Adapter transports requests and events without selecting agents or invoking personal tools.

### Task 3: Project role and contract through runtime generation

**Purpose:**
- Keep generated Nanobot/OpenClaw surfaces aligned from canonical sources.

**Task Function:**
- Runtime projection and generated-surface reconciliation.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: existing generator owns all runtime projections.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: existing generator and contract validators.

**Specification Coverage:**
- Generated files are projections; Nanobot role is relay; CoS role remains policy/task authority; Project OS role remains execution authority; transport metadata stays symmetric.

**Required Skills:**
- `skill-central-config-layer`

**Files And Symbols:**
- Inspect: `scripts/generate_runtime_surface.py`, `adapters/nanobot/manifest.toml`, `adapters/openclaw/manifest.toml`
- Modify: `scripts/generate_runtime_surface.py`, canonical agent templates, adapter manifests
- Verify: `generated_runtime/nanobot/`, `generated_runtime/openclaw/`, `tests/test_generate_openclaw_surface.py`

**Dependencies:**
- Task 1 config schema.

**Authority:**
- Preauthorized local actions: update generator, canonical templates, manifests, generated files, and generator tests.
- Stop for: direct edits to generated files without generator changes or policy duplication between runtimes.

**Steps:**
- [x] Generate role-specific runtime identity/policy from the frontend entry.
- [x] Generate relay contract metadata for Nanobot and CoS task-authority metadata for OpenClaw.
- [x] Generate repository-targeting contract metadata without embedding absolute repository paths.
- [x] Ensure adding a fixture frontend changes data/config only, not generator control flow.
- [x] Regenerate all maintained runtime surfaces.

**Verification:**
- [x] `python scripts/generate_runtime_surface.py --check`
- [x] `python scripts/validate_repo_contracts.py`
- Expected: generated output is current; Nanobot declares relay-only role; OpenClaw declares CoS role.

**Exit Criteria:**
- No runtime surface claims Nanobot owns CoS orchestration.

### Task 4: Make Nanobot relay-only

**Purpose:**
- Enforce boundary in Nanobot runtime, not through model instructions alone.

**Task Function:**
- Runtime integration and capability restriction.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: integration depends on installed Nanobot capability surface.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: runtime config inspection and local smoke test.

**Specification Coverage:**
- Nanobot forwards messages and commands; Nanobot does not execute orchestration.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `scripts/start_nanobot.ps1`, installed Nanobot plugin/channel hook surface
- Modify: `scripts/start_nanobot.ps1`, tracked Nanobot adapter/config projection as supported
- Verify: local `~/.nanobot/config.json` and Nanobot gateway logs

**Dependencies:**
- Tasks 2–3 complete.

**Authority:**
- Preauthorized local actions: inspect installed Nanobot capabilities, update tracked launcher/projection, and apply reversible local config changes.
- Stop for: no deterministic channel interception hook; do not substitute prompt-only rules, MCP forwarding, or a second Telegram bot.

**Steps:**
- [x] Prove Nanobot’s supported deterministic channel hook or plugin point and effective capability-deny mechanism.
- [x] Route inbound Telegram text and commands to the CoS adapter unchanged.
- [x] Preserve user-specified `repository_id`, `repository_ref`, and `access_mode` as metadata only.
- [x] Route relay events to the originating Telegram conversation.
- [x] Disable Nanobot task tools, Herdr access, local orchestration paths, and decision memory for relay sessions.
- [x] Preserve separate Nanobot memory store without using it for CoS decisions.

**Verification:**
- [x] Inspect effective Nanobot config and gateway startup logs.
- [x] Assert no local task, filesystem, Git, Herdr, memory-decision, or agent-selection capability is exposed.
- [ ] Send one test message and one command through Telegram in an authorized chat.
- Expected: CoS receives exact payload; Nanobot emits only CoS events; no local tool or agent-selection call occurs.

**Exit Criteria:**
- Nanobot cannot complete a task locally when CoS is unavailable; it reports relay failure instead.

**Recorded Result (2026-09-07):**
- Generated Nanobot tool registry declares `capabilities = []`; edge templates prohibit local model, memory, filesystem, Git, Herdr, task, and agent-selection use.
- Fresh installed-runtime probe passed: `NANOBOT_PRE_AGENT_HOOK` handled authorized text before `MessageBus` publication; hook-enabled bus count was `0`, hook-disabled count was `1`.
- Fresh adapter boundary probe passed typed event rendering and explicit relay failure handling.
- Gateway restarted after adapter fix; current process is running and startup
  completed without a new adapter exception.
- Live authorized Telegram message and command smoke remains open; no live message was sent during this execution.

### Task 5: Project OS integration and end-to-end proof

**Purpose:**
- Prove local Codex CoS handoff to the selected repository without making
  Nanobot own Project OS runtime mechanics.

**Task Function:**
- Local Codex CoS handoff and Project OS integration.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: Personal CoS is user-callable through its repository-owned skill; Project OS CoS remains an external repository-owned execution boundary.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: adapter contract proof supplied by CoS owner.

**Specification Coverage:**
- Personal CoS owns personal memory, prioritization, approvals, aggregation, and
  personal routing. Project OS owns canonical work truth, repository access,
  execution policy, Project CoS activation, Herdr, MAIN AGENT selection, lane
  execution, and acceptance proof.

**Required Skills:**
- `skill-personal-chief-of-staff`, `skill-personal-routing`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `docs/operating_system/rules/delegation-rule.md`, `docs/operating_system/rules/authority-boundary-rule.md`, `codex exec --help`
- Modify: local contract/projection surfaces only; do not fork or duplicate shared `skill-chief-of-staff`
- Verify: local Codex CoS runner with `--cd`, `personal.dispatch.v1` handoff, and normalized JSONL progress evidence

**Dependencies:**
- Tasks 2–4 and the local Codex CLI capability gate.

**Authority:**
- Preauthorized local actions: document the CoS contract, create local compatibility fixtures, and run the existing Codex CLI runner; do not mutate shared skill files or external runtime state.
- Stop for: unavailable local Codex CLI, unresolved authorization, missing typed event schema, unavailable Project OS/Herdr capability, or any request to move routing logic into Nanobot.

**Steps:**
- [x] Local runner consumes edge envelopes and preserves `request_id`, `conversation_id`, and raw text.
- [x] Local runner preserves `repository_id`, `repository_ref`, and `access_mode` as semantic intent, while resolving only registered roots.
- [x] Local runner invokes `codex exec --json --cd <registered-repo> -` once per request.
- [ ] Codex CoS validates repository intent and decides whether Project OS work is needed.
- [ ] Local runner emits `accepted` before invocation and forwards progress/terminal events with monotonic sequence.
- [ ] Codex CoS owns decisions; Herdr remains internal and activates only when CoS assigns MAIN AGENT work.
- [ ] Local runner reports `/status`, `/cancel`, and `/approve` results without owning task state.

**Verification:**
- [ ] Local runner supplies one `personal.edge.v1` request to Codex CLI with the selected repository as `--cd`.
- [ ] Codex CoS supplies executable proof for one read request and one authorized write request against registered repositories.
- [ ] Verify Codex CoS selects the execution path, Herdr supervises only assigned agent work, and evidence returns without transferring control to Nanobot.
- Expected: Nanobot forwards; Codex CoS interprets and decides; Project OS/Herdr executes when needed; Nanobot receives observable progress and final state.

**Exit Criteria:**
- Local Codex CoS receives repository-scoped requests and returns protocol-compliant typed events; CoS/Project OS acceptance remains authoritative.

**Recorded Result (2026-09-07):**
- `personal-os` and `job-project` read-only smokes each emitted ordered
  `accepted`, `progress`, and `completed` events through direct
  `codex exec --json --cd <registered-repo> -`.
- Remaining proof requires user-authorized Telegram smoke and repository-scoped
  CoS/Project OS acceptance evidence; this repository cannot provide that
  external boundary proof.

### Task 6: Reconcile docs and complete verification

**Purpose:**
- Leave one operational procedure for start, stop, restart, failure, and new-bot onboarding.

**Task Function:**
- Acceptance verification and operational documentation.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: final repository reconciliation.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: final verification skill owns completion proof.

**Specification Coverage:**
- Minimum management, symmetry, generated-source consistency, rollback, and operator visibility.

**Required Skills:**
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `README.md`, `docs/operating_system/procedures/`
- Modify: `README.md`, relevant procedure documentation, focused tests
- Verify: all changed files and clean Git state

**Dependencies:**
- Tasks 1–5 complete.

**Authority:**
- Preauthorized local actions: update tracked docs/tests and run complete local verification.
- Stop for: failed required proof, stale generated output, unrecorded scope change, or unresolved local runner blocker.

**Steps:**
- [x] Document one Nanobot command path and one CoS failure/reconnect path.
- [x] Document repository selection by canonical ID and read/write authorization rules.
- [x] Document Project OS status and progress observation without exposing Project OS internals or Herdr to Nanobot.
- [x] Document new frontend onboarding as one config entry plus adapter projection.
- [ ] Run focused tests, full tests, generator check, and contract validation.
- [x] Record deviations and external CoS evidence in this plan.

**Verification:**
- [ ] `python -m unittest discover -s tests -p "test_*.py"`
- [ ] `python scripts/generate_runtime_surface.py --check`
- [ ] `python scripts/validate_repo_contracts.py`
- Expected: all required checks pass and no generated, credential, or runtime-state files are tracked.

**Exit Criteria:**
- Verification returns `verified`; only then request commit and push.

**Recorded Result (2026-09-07):**
- Focused changed-surface tests: `27` passed.
- All non-calendar tests: `43` passed.
- Full discovery remains blocked by pre-existing `MemoryError` importing
  `mcp`/`lark` through `tests/test_calendar_mcp_server.py` on Python 3.13.
- Runtime generation, repository contract validation, diff validation, and both
  registered-repository launcher smokes passed.

## Verification

- `python -m unittest discover -s tests -p "test_*.py"`
- `python scripts/generate_runtime_surface.py --check`
- `python scripts/validate_repo_contracts.py`
- Edge proof: forward message, observe typed CoS events, handle reconnect/status, approval, cancel, failure, and unauthorized request without inferring state from terminal text.
- Local runner proof: resolves registered ID, rejects unknown ID/path traversal/UNC path/symlink escape, and invokes Codex with the selected root as `--cd`.
- Runtime proof: Nanobot has relay role, no local orchestration tools, and reports CoS events to Telegram.
- CoS proof: Codex CoS decides whether Project OS work is needed; Herdr supervises only assigned MAIN AGENT lanes; Nanobot receives progress plus terminal event.

## Completion Criteria

1. `personal.edge.v1` and frontend relay settings have one canonical owner; existing `personal.dispatch.v1` remains the Personal CoS → Project OS handoff.
2. Approved repositories have one canonical ID-to-root registry.
3. Nanobot forwards messages, commands, and repository metadata without interpreting or executing them.
4. Codex CoS validates personal intent and owns memory decisions, prioritization, approvals, and aggregation; Project OS validates repository access and owns execution policy, lane selection, Herdr, lane execution, and acceptance.
5. Stable `request_id` plus local runner state support adapter restart and status recovery; Herdr remains transient Project OS observation.
6. New frontend or repository onboarding needs configuration plus projection, not new orchestration logic.
7. Credentials, private memory, sessions, absolute roots, and runtime state remain outside Git.
8. All task-local and final verification passes with evidence recorded.
9. No commit or push occurs until verified completion and explicit Git disposition.
