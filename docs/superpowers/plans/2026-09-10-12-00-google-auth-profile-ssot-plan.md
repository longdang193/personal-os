---
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: active
layer: change
name: google-auth-profile-ssot
targets:
  - agents/review.toml
  - agents/normal.toml
  - repo_config/planning_artifact_schema.yaml
  - repo_config/tool_registry.toml
  - scripts/validate_repo_contracts.py
  - scripts/read_google_auth_profile.py
  - scripts/check_google_auth.ps1
  - scripts/mail_mcp_server.py
  - scripts/calendar_mcp_server.py
  - README.md
  - .agents/skills/skill-mail-management/SKILL.md
  - generated_runtime/openclaw/TOOL_REGISTRY.toml
  - generated_runtime/openclaw/skills/skill-mail-management/SKILL.md
  - tests/test_validate_repo_contracts.py
  - tests/test_google_auth_profile.py
  - tests/test_generate_openclaw_surface.py
  - tests/test_mail_mcp_server.py
  - tests/test_calendar_mcp_server.py
---

# Google Auth Profile SSOT

## Goal

Make one non-secret Google Workspace auth profile the source of truth for
personal Gmail and Google Calendar. Make Nanobot and OpenClaw consume the same
profile through existing startup preflight and generated runtime surfaces.
Prevent broad or invalid OAuth scope requests, preserve Calendar access during
Gmail repair, and keep provider failures isolated from student Himalaya mail.

## Implementation Outcomes

### One registry-owned Google auth profile

`repo_config/tool_registry.toml` declares one `[[auth_profiles]]` entry with
`id = "google-workspace"`, provider identity, CLI identity, status arguments,
login arguments, and these exact scopes:

- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/calendar`

Tool `google-workspace` and accounts `personal` plus `google-calendar` reference
that same profile. No token, client secret, OAuth code, callback URL, account
address, or other secret enters Git.

The profile contract is exact and validated before consumers run:

| Field | Type and allowed value |
| --- | --- |
| `id` | non-empty lowercase kebab-case string; unique within registry |
| `provider` | exact string `google-workspace` |
| `command` | non-empty executable name; current value `gws` |
| `status_args` | non-empty string list; current value [`auth`, `status`] |
| `login_args` | non-empty string list; current value [`auth`, `login`] |
| `scopes` | exact, duplicate-free string list containing only the Gmail read-only and Calendar scopes above |
| `redact_output` | exact boolean `true`; helper never returns command output |

`auth_profile` is an explicit foreign-key reference to `auth_profiles.id` on
auth-consuming tools and accounts. Existing `provider` remains provider
identity and is not overloaded as an auth-profile reference. The current
profile is referenced by `google-workspace`, `mail-runtime`,
`calendar-runtime`, `personal`, and `google-calendar`; student Himalaya keeps
its existing provider and has no Google profile reference. The helper JSON
contract exposes only `id`, `provider`, `command`, `status_args`, `login_args`,
and `scopes`; output is schema-validated and redacted by construction.

### Registry-backed runtime behavior

`scripts/read_google_auth_profile.py` uses stdlib `tomllib` to expose the
validated profile as JSON. `scripts/check_google_auth.ps1` consumes that output
instead of carrying scope text or repair instructions locally. Both startup
scripts keep using this single preflight. README and the mail skill refer to
the registry-backed repair path, not copied OAuth scope literals. OpenClaw
output remains generated from canonical sources; Nanobot remains relay-only.

### Symmetric failure handling and proof

Auth states use one shared contract: `ready`, `missing`, `expired`,
`invalid_scope`, and `provider_unavailable`. Google failure warns and degrades
Google mail/calendar only. Student mail remains available. Focused tests prove
registry shape, shared profile references, Calendar-scope preservation, missing
CLI behavior, expired/invalid status handling, generated-surface consistency,
and absence of secret or callback data in output paths.

Failure precedence is deterministic. Preflight normalizes captured stdout and
stderr to lowercase, strips ANSI control sequences, and never emits either
stream. Rules run in this order: missing executable → `missing`; a successful
status response with boolean `token_valid = true` → `ready`; output matching
`invalid_scope`, `invalid scope`, `scope name is invalid`, `unsupported scope`,
or `outside the domain of this legacy api` → `invalid_scope`; output matching
`token expired`, `invalid_grant`, `authentication failed`, `auth required`,
`credential`, or `permission denied`, or a successful status response with
boolean `token_valid = false` → `expired`; timeout, malformed JSON, unexpected
exception, or any other non-zero result → `provider_unavailable`. Matching is
case-insensitive over the combined streams, and the first matching rule wins.
Non-boolean `token_valid` is malformed input and yields `provider_unavailable`.
Google failure is warning-only for both startup callers, so student mail remains
independently usable.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-chief-of-staff`, `skill-systematic-debugging`, `skill-test-driven-development`, `skill-central-config-layer`, `skill-backend-verification`, `skill-code-standards`, `skill-verification-before-completion`, `skill-plan-document-reviewer`
- Isolation: `current checkout for read-only review; isolated Git worktree for write lane`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit listed tracked files, regenerate declared OpenClaw output, preserve unrelated workspace changes, and run declared local tests, validators, syntax checks, and diff inspection
- User-approval actions: external OAuth, provider authentication, real mail/calendar writes, commit, push, merge, discard, cleanup, or changes outside listed targets
- Parallel ownership: none; registry, preflight, docs, generated output, and tests share one contract
- Sequential fallback: confirm registry contract before changing consumers; update canonical sources before generation; run focused proof before final repository checks

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `master`
- Base commit: `9de9487`
- Expected workspace: `master` at `9de9487` with current plan and restored `repo_config/planning_artifact_schema.yaml` committed; preserve these unrelated paths exactly during execution: `.serena/project.yml` (`ECC7D3AD7DB856BDC15FA53CEB99096B7E301A7F469D887F0180DDD8F93EFEF2`), `agents/normal.toml` (`75CC63E3C6CE21EC6D98A034E6191005FF46AD55B1F1400B33453E273082CDED`), `agents/review.toml` (`1C8BCAE300D2FFB6E1E546F6325579023E8BED4FEBAEE32EE867FFAD23E1D494`), `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `agents/high.toml`, `agents/low.toml`, `agents/ui.toml`, `agents/xhigh.toml`, `repo_config/publication-config.json`, `scripts/new_audit.ps1`, `scripts/new_brainstorming_report.ps1`, `scripts/setup_hooks.ps1`, and `scripts/setup_hooks.sh`; current status/hash inventory is the preservation boundary, and the plan plus named execution targets are the only allowed changes
- Next action: dispatch independent plan review through Herdr; activate implementation lane only after review `PASS`
- Blockers: `none`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 0 | `completed` | current | `codex` | none | planning validator | `repo_config/planning_artifact_schema.yaml` restored |
| Task 1 | `pending` | current | `unresolved` | Task 0 | registry contract tests | pending |
| Task 2 | `pending` | current | `unresolved` | Task 1 | preflight failure-state tests and PowerShell syntax | pending |
| Task 3 | `pending` | current | `unresolved` | Task 2 | canonical docs plus generated-surface drift check | pending |
| Task 4 | `pending` | current | `unresolved` | Task 3 | focused suite, validator, generation check, diff check | pending |

## Task Breakdown

### Task 0: Restore planning validation schema

**Purpose:**
- Restore required repository validation input before delegated work begins.

**Task Function:**
- Coordination prerequisite repair.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: exact canonical schema is available in sibling Project OS repositories with matching content hash.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: shared lifecycle validator is the direct proof.

**Specification Coverage:**
- Git-tracked plan validation and safe CoS dispatch gate.

**Required Skills:**
- `none`

**Files And Symbols:**
- Inspect: `C:\Users\HOANG PHI LONG DANG\repos\project-OS-starter\repo_config\planning_artifact_schema.yaml`, shared `planning_artifact_schema.py`
- Modify: `repo_config/planning_artifact_schema.yaml`
- Verify: shared repository and planning validators

**Dependencies:**
- Existing repository plans and shared Project OS validation contract.

**Authority:**
- Preauthorized local actions: restore exact non-secret validation schema and run local validator checks.
- Stop for: schema redesign, unrelated config migration, or changes outside the named file.

**Steps:**
- [x] Step 1: Restore schema with SHA-256 matching `project-OS-starter` and `JOB-PROJECT` copies.
- [x] Step 2: Re-run planning and repository contract validation.

**Verification:**
- [x] `py -B C:\Users\HOANG PHI LONG DANG\.agents\project-os\scripts\validate_planning_lifecycle.py --repo-root .`
- Expected: existing plan artifacts parse and active plan contract validates.

**Exit Criteria:**
- Required planning schema exists, matches known canonical content, and validation gate can run.

### Task 1: Define and validate shared auth profile

**Purpose:**
- Establish one non-secret auth contract for Gmail and Calendar.

**Task Function:**
- Registry contract design and validation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: existing TOML registry and validator are local, bounded, and low ambiguity.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused registry tests provide direct proof.

**Specification Coverage:**
- One auth profile, exact least-privilege scopes, symmetric mail/calendar references, and secret exclusion.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-central-config-layer`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `repo_config/tool_registry.toml`, `scripts/validate_repo_contracts.py:tool_registry_issues`, `tests/test_validate_repo_contracts.py`, `scripts/mail_mcp_server.py:_gws_command`, `scripts/mail_mcp_server.py:_gws_call`, `scripts/calendar_mcp_server.py:_gws_command`, `scripts/calendar_mcp_server.py:_gws_call`, and their provider boundary tests
- Modify: `repo_config/tool_registry.toml`, `scripts/validate_repo_contracts.py:tool_registry_issues`, `tests/test_validate_repo_contracts.py`, `tests/test_mail_mcp_server.py`, `tests/test_calendar_mcp_server.py`
- Verify: parsed registry, validator output, all `gws auth login` occurrences in tracked canonical and generated files

**Dependencies:**
- Current registry entries `google-workspace`, `mail-runtime`, `personal`, and `google-calendar`.
- Current failure root cause: duplicated auth command text and broad/bare OAuth login path can request unsupported scopes for personal Gmail.

**Authority:**
- Preauthorized local actions: modify registry schema, validator, and focused tests; use synthetic registry objects and temporary copies only.
- Stop for: storing secrets or private account data, adding a second auth store, changing provider permissions, or changing mail/calendar capabilities.

**Steps:**
- [ ] Step 1: Add one `[[auth_profiles]]` entry matching the exact field/type/allowed-value contract above; keep all command and scope facts in this registry entry.
- [ ] Step 2: Add `auth_profile = "google-workspace"` to `google-workspace`, `mail-runtime`, `calendar-runtime`, `personal`, and `google-calendar`; preserve `provider` as provider identity and leave student Himalaya unlinked.
- [ ] Step 3: Extend `tool_registry_issues` to reject missing, duplicate, malformed, unsupported, unreferenced, secret-bearing, or mismatched profile references and to enforce the helper JSON contract.
- [ ] Step 4: Search every tracked canonical/generated `gws auth`, scope, and repair literal; assign executable literals to Task 2, documentation literals to Task 3, and reject every duplicate outside the registry.
- [ ] Step 5: Add tests proving symmetric Gmail/Calendar references, exact scope preservation, provider/profile distinction, student isolation, unsafe-profile rejection, and secret-field rejection.
- [ ] Step 6: Prove `mail_mcp_server.py` and `calendar_mcp_server.py` resolve the same registry profile/provider boundary rather than carrying independent Google command or auth policy.

**Verification:**
- [ ] `python -m unittest tests/test_validate_repo_contracts.py`
- Expected: registry contract tests pass; malformed profiles fail with actionable validator errors; current registry passes.

**Exit Criteria:**
- Registry owns all Google auth facts needed by consumers, and validator prevents drift or unsafe profile shape.

### Task 2: Make startup preflight consume registry profile

**Purpose:**
- Remove duplicated OAuth scope and repair-command literals from PowerShell behavior while preserving non-blocking startup.

**Task Function:**
- Shared preflight integration.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: one existing helper and two existing callers; no new auth service needed.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: direct script checks plus focused tests cover bounded PowerShell behavior.

**Specification Coverage:**
- Same preflight for Nanobot and OpenClaw; common states `ready`, `missing`, `expired`, `invalid_scope`, `provider_unavailable`; student mail isolation; safe, non-secret diagnostics.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `scripts/check_google_auth.ps1`, `scripts/start_nanobot.ps1`, `scripts/start_openclaw.ps1`, `tests/test_validate_repo_contracts.py`
- Modify: `scripts/check_google_auth.ps1`, `tests/test_validate_repo_contracts.py`
- Verify: `scripts/start_nanobot.ps1`, `scripts/start_openclaw.ps1`, `scripts/mail_mcp_server.py`, `scripts/calendar_mcp_server.py`, PowerShell parser, mocked status-output cases, and student-provider routing

**Dependencies:**
- Task 1 registry profile and validator.
- Existing startup callers must remain unchanged in control flow: preflight warns and does not block student-only Himalaya mail.

**Authority:**
- Preauthorized local actions: modify preflight and tests; run mocked/local CLI checks without authenticating or writing provider state.
- Stop for: automatic OAuth launch, callback listener management, token inspection, retries beyond one status check, or startup blocking on Google failure.

**Steps:**
- [ ] Step 1: Add `scripts/read_google_auth_profile.py:load_profile` using stdlib `tomllib`; validate the exact profile contract and emit only the documented non-secret JSON fields for PowerShell.
- [ ] Step 2: Read profile data through that helper; construct status and repair text from registry values, including `--scopes` from the profile rather than embedding scope literals.
- [ ] Step 3: Implement the declared precedence for stdout and stderr: missing executable, `token_valid`, expired/auth markers, invalid-scope markers, then timeout/malformed JSON/exception/other command failure; never print raw provider output.
- [ ] Step 4: Own and remove executable duplicates found in Task 1's search, while keeping one shared `check_google_auth.ps1` call in both startup scripts; update both MCP bridges to consume the same profile/provider contract without duplicating auth policy; prove warning-only behavior and student-mail continuation.
- [ ] Step 5: Test valid, expired, invalid-scope, missing executable, provider failure, timeout, malformed JSON, stderr-only failure, thrown exception, non-boolean token status, and secret/callback redaction cases with temporary local shims only.

**Verification:**
- [ ] `python -m unittest tests/test_google_auth_profile.py`
- [ ] Run preflight with temporary `gws` shims for valid token, expired token, missing `gws`, invalid scope output, and provider command failure.
- [ ] `powershell -NoProfile -Command "[System.Management.Automation.Language.Parser]::ParseFile('scripts/check_google_auth.ps1',[ref]$null,[ref]$null) | Out-Null"`
- Expected: each case emits safe actionable output, only `ready` reports ready, no raw provider secrets or callback URLs appear, and parser returns no errors.

**Exit Criteria:**
- Preflight derives auth instructions from the registry, handles all declared states symmetrically, and remains non-blocking and secret-safe for both runtimes.

### Task 3: Remove documentation duplication and regenerate runtime surfaces

**Purpose:**
- Make user guidance point to one registry-backed repair path and keep OpenClaw projection synchronized.

**Task Function:**
- Canonical documentation and generated-surface reconciliation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: existing README and canonical mail skill own user guidance; generator already projects OpenClaw output.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: generator drift check and text assertions provide direct proof.

**Specification Coverage:**
- SSOT, symmetry across runtimes and Google features, no manual callback guidance, and no duplicated OAuth scope literals.

**Required Skills:**
- `skill-central-config-layer`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `README.md`, `.agents/skills/skill-mail-management/SKILL.md`, `scripts/generate_runtime_surface.py:adapter_output_files`, `tests/test_generate_openclaw_surface.py`
- Modify: `README.md`, `.agents/skills/skill-mail-management/SKILL.md`, `tests/test_validate_repo_contracts.py`, `tests/test_generate_openclaw_surface.py`
- Generate: `generated_runtime/openclaw/TOOL_REGISTRY.toml`, `generated_runtime/openclaw/skills/skill-mail-management/SKILL.md`
- Verify: no stale bare/broad OAuth instructions in tracked source or generated output

**Dependencies:**
- Task 2 preflight command and state contract.
- Canonical `.agents/skills` source remains authoritative; never edit generated OpenClaw files directly.

**Authority:**
- Preauthorized local actions: update listed canonical docs/tests, regenerate OpenClaw output, and inspect tracked text.
- Stop for: runtime-specific policy duplication, manual OAuth URL/callback instructions, generated-file direct edits, or changes to Nanobot personal-tool exposure.

**Steps:**
- [ ] Step 1: Replace README's copied scope command and every documentation-level duplicate with registry-backed preflight guidance; explain one shared profile for Gmail plus Calendar without exposing callback, URL, token, or account data.
- [ ] Step 2: Update mail recovery guidance to request only the safe profile-backed repair path; retain partial-result and student-mail behavior.
- [ ] Step 3: Regenerate all runtime surfaces from canonical sources; assert generated auth-profile fields, canonical/generated registry equality including profile references and exact scopes, canonical/generated mail-skill equality, and Nanobot relay-only boundaries.
- [ ] Step 4: Re-run the full tracked-text search and record that only the registry owns Google login/scope literals and no bare OAuth/callback instruction remains.

**Verification:**
- [ ] `python scripts/generate_runtime_surface.py`
- [ ] `python scripts/generate_runtime_surface.py --check`
- Expected: generated OpenClaw registry contains the single auth profile; canonical skill and generated skill match; no stale duplicated auth command remains.

**Exit Criteria:**
- Documentation and generated surfaces contain no independent Google scope policy and both runtimes expose the same registry-backed guidance.

### Task 4: Final integration verification

**Purpose:**
- Prove root-cause fix, shared callers, failure isolation, generated consistency, and scope boundaries before execution completion.

**Task Function:**
- Final acceptance verification.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: lead controller owns fresh evidence and Git scope reconciliation.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: repository tests, validators, syntax checks, and diff inspection are sufficient.

**Specification Coverage:**
- All implementation outcomes, symmetry rules, security boundaries, and preserved unrelated changes.

**Required Skills:**
- `skill-backend-verification`
- `skill-verification-before-completion`
- `skill-plan-document-reviewer`

**Files And Symbols:**
- Inspect: all plan targets, `git diff`, `git status`, all tracked `gws auth` references
- Modify: none unless an in-scope verification defect is found
- Verify: focused tests, generator, validator, PowerShell parser, and diff boundaries

**Dependencies:**
- Tasks 1–3 complete and accepted by lead controller.

**Authority:**
- Preauthorized local actions: run local tests, validators, syntax checks, generator checks, and inspect status/diff.
- Stop for: provider authentication, real mail/calendar operations, unrelated changes, or any request to clean `.serena/project.yml`.

**Steps:**
- [ ] Step 1: Run focused registry, generation, and mail-contract tests.
- [ ] Step 2: Run repository validation and PowerShell syntax checks.
- [ ] Step 3: Inspect `git diff --check`, changed paths, generated headers, and tracked auth references; record deviations or deferrals.

**Verification:**
- [ ] `python -m unittest tests/test_validate_repo_contracts.py tests/test_google_auth_profile.py tests/test_generate_openclaw_surface.py tests/test_mail_mcp_server.py`
- [ ] `python scripts/generate_runtime_surface.py --check`
- [ ] `python scripts/validate_repo_contracts.py`
- [ ] `python -m py_compile scripts/validate_repo_contracts.py scripts/mail_mcp_server.py scripts/calendar_mcp_server.py`
- [ ] PowerShell parser check for `scripts/check_google_auth.ps1`, `scripts/start_nanobot.ps1`, and `scripts/start_openclaw.ps1`
- [ ] `git diff --check`
- Expected: all checks pass; generated output is current; no secret/callback data appears; stderr, exception, malformed-input, timeout, and student-isolation proofs pass; `.serena/project.yml` and all unrelated files remain preserved.

**Exit Criteria:**
- Fresh local evidence proves shared auth profile ownership, startup behavior, failure isolation, generated consistency, and no out-of-scope mutation. No commit or push occurs under this plan without separate user authorization.

## Verification

- `python -m unittest tests/test_validate_repo_contracts.py tests/test_google_auth_profile.py tests/test_generate_openclaw_surface.py tests/test_mail_mcp_server.py`
- `python scripts/generate_runtime_surface.py --check`
- `python scripts/validate_repo_contracts.py`
- `python -m py_compile scripts/validate_repo_contracts.py scripts/read_google_auth_profile.py scripts/mail_mcp_server.py scripts/calendar_mcp_server.py`
- PowerShell parser checks for all three auth/startup scripts
- `git diff --check`
- `rg -n -S "gws auth login|gmail.readonly|auth_profile|callback|localhost" README.md .agents scripts repo_config generated_runtime --glob '!*.pyc'`

## Completion Criteria

The plan is ready for completion verification when:

1. one non-secret registry auth profile owns Google CLI identity, operations, and exact scopes; `read_google_auth_profile.py` is the only TOML-to-runtime bridge
2. personal Gmail and Google Calendar reference that profile symmetrically
3. preflight derives status and repair behavior from the profile and never logs secrets, OAuth codes, callback URLs, or raw provider output
4. `ready`, `missing`, `expired`, `invalid_scope`, and `provider_unavailable` behavior is proven without blocking student mail
5. README and canonical mail guidance contain no independent Google scope policy or bare OAuth instruction
6. generated OpenClaw surfaces match canonical sources and Nanobot remains relay-only
7. focused regression tests, backend boundary proof, generation checks, repository validation, syntax checks, and diff checks pass
8. no auth service, callback listener, token inspector, retry loop, second token store, or new dependency is added
9. unrelated `.serena/project.yml` modification remains untouched
