# Content Monitoring

Use one `content-poller` command for RSS and Apify Instagram sources.

## Configuration

- Keep source watchlists in `~/.personal-os/watch_sources.toml`.
- Keep `APIFY_TOKEN` in the local environment or ignored `.env` file.
- Use one enabled `[[sources]]` entry per Instagram profile.
- Keep `resultsLimit` at `5` unless source volume requires more.

## Runtime

The Personal CoS launcher runs the poller directly for tracked-update requests.
No MCP server or content service is required. Manual invocation:

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

Review remains read-only. Personal CoS reports poller events and provider
errors separately. A failed poll is not a no-update result, and stale web
search must not replace a failed tracked-source poll.
