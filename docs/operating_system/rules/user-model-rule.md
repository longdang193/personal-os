# User Model Rule

- `USER.md` is private mutable data, never generated from this repository.
- Store stable preferences and profile facts only.
- Prefer provenance and recency for facts that can change.
- Conflicting newer user instructions supersede older preferences.
- Secrets, credentials, raw transcripts, and transient events do not belong in
  the user model.

