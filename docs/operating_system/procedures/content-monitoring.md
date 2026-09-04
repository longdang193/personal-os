# Content Monitoring

Use one `content-poller` runtime for RSS and Apify Instagram sources.

## Configuration

- Keep source watchlists in `~/.personal-os/watch_sources.toml`.
- Keep `APIFY_TOKEN` in the local environment or ignored `.env` file.
- Use one enabled `[[sources]]` entry per Instagram profile.
- Keep `resultsLimit` at `5` unless source volume requires more.

## Runtime

OpenClaw schedules the poller. Run from the repository checkout or use an
absolute script path when the Gateway working directory is the OpenClaw
workspace:

```powershell
python3 scripts/poll_content_updates.py --source-id <source-id> --max-items 5 --apify-timeout 120
```

RSS uses its separate `20` second timeout. Apify uses `120` seconds. The
poller emits `content.update.v1` JSON lines, then `skill-update-review` reviews
them as untrusted source data. Local bounded state suppresses duplicates.

## Bootstrap and Verify

Run `--bootstrap` once for each new source. It records existing items without
notifications. Run again without `--bootstrap`; unchanged items must emit no
events. Check state under `~/.personal-os/content-state/`.

## Delivery

Review remains read-only. Personal CoS proposes authorized follow-ups. Current
Instagram monitoring can run silently when no OpenClaw delivery destination is
configured; configure an explicit channel and destination before expecting
Telegram notifications.
