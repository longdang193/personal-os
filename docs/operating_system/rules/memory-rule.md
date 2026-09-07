# Memory Rule

- `MEMORY.md` and `memory/` are private mutable state outside Git.
- Each runtime owns its own private memory store; OpenClaw and Nanobot do not
  automatically share or synchronize memory.
- Personal OS owns memory policy and boundaries, not runtime memory contents.
- Store curated durable knowledge, not exhaustive transcripts.
- Keep source, confidence, provenance, and expiry when practical.
- Canonical repository sources and explicit user instructions override memory.
- Do not expose unrelated memory to project agents.
