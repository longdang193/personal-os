# Secrets Rule

- Never commit credentials, tokens, private keys, or session state.
- Never place secrets in `USER.md`, `MEMORY.md`, delegation payloads, logs, or
  generated runtime files.
- Use local secret stores and provider-native authentication.
- Redact secrets before saving diagnostics or sharing task context.

