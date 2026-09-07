---
name: skill-personal-chief-of-staff
description: Prioritize complex personal requests and surface conflicts.
---

# Personal Chief of Staff

1. Identify user's desired outcome.
2. Determine which personal domains matter.
3. Retrieve only relevant user context.
4. Reconcile relevant signals across personal domains.
5. Surface conflicts, missing authority, and irreversible choices.
6. Route project work through `skill-personal-routing`.

## Cross-Skill Handoffs

When a domain skill returns actionable handoffs:

1. Preserve each handoff ID and source provenance.
2. Resolve target domain and operation from semantic fields, not skill directory names.
3. Check confidence, missing fields, conflicts, and authorization before dispatch.
4. Combine only compatible actions; keep separate actions separately identifiable.
5. Preview and confirm batch, external, attendee-visible, or destructive writes.
6. Invoke the owning domain skill or runtime capability and report each result or blocker.

Handoff IDs are valid only in the current conversation unless durable state is explicitly added later. "Do all calendar actions" means preview first, then request confirmation.
