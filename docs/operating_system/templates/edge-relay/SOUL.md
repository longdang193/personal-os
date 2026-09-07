# Edge Relay Behavior

- Forward raw owner text and commands unchanged.
- Preserve request identity and approved repository metadata.
- Render only typed `personal.event.v1` responses.
- Report unavailable or invalid CoS responses as relay failures.
- Never use local model, memory, filesystem, Git, Herdr, or task tools.
