---
name: skill-personal-routing
description: Route project requests to target Project OS entrypoints.
---

# Personal Routing

1. Identify target project and requested outcome.
2. Pass user request, personal constraints, and minimum necessary context.
3. Do not select project plan, task, executor, profile, model, worktree, branch, or Herdr lane.
4. Let the target Project OS determine project acceptance and evidence requirements.
5. Review returned status, blockers, result summary, and evidence references before reporting completion.

## Minimal Dispatch Contract

```text
personal.dispatch.v1

request_id
target
user_request
personal_constraints
context_capsule?
```

Do not add project-internal planning, execution, or acceptance fields to this payload.
