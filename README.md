# Help-center → Gemini File Search sync (OptiBot mini-clone)

Scrapes the Zendesk help center, converts articles to Markdown, uploads only the delta to a Gemini File Search store. Runs once and exits 0.

## Quick start (needs only Docker)
```
./start.sh        # first run creates .env: put GEMINI_API_KEY in it (aistudio.google.com/apikey), run again
```
It builds the image, syncs the help center (the same job the VPS runs daily), then serves the chat UI at http://127.0.0.1:8000. The store is found by display name (`optibot-kb`) in the key's own Google project and created on the first run; set `FILE_SEARCH_STORE` only to point at a specific store.

## Individual commands
```
docker run --rm --env-file .env -e DRY_RUN=1 -v "$PWD/out:/app/out" ds-sync-x7q   # scrape only; Markdown lands in ./out
docker run --rm --env-file .env ds-sync-x7q                                       # the daily job: scrape + delta sync, exits 0
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest && .venv/bin/python -m pytest -q   # unit tests, no network
```

## How it works
- **Scrape**: `GET /api/v2/help_center/en-us/articles.json` (paginated, drafts skipped) → `markdownify` → `out/<id>-<slug>.md`. Each file starts with `# Title` + `Article URL: <html_url>` so the bot can cite it. Headings, code, tables, links preserved; only the article body is taken (no nav/ads).
- **Delta**: sha256 of the Markdown is stored in each document's `custom_metadata` (`article_id`, `hash`) → job is stateless. New id = added; changed hash = updated (new doc uploaded, then old deleted); same hash = skipped.
- **Chunking**: whitespace chunking, 500 tokens max / 50 overlap (API cap is 512 per chunk). Median article is ~6.7k chars (~1.7k tokens), so ~3-4 chunks keep each procedure section together; 50 overlap keeps a heading with its first step. Gemini exposes no chunk count; the log reports an estimate (~4 chars/token).
- **Log line**: `added=.. updated=.. skipped=.. files_embedded=.. est_chunks=..`

## Daily job
Docker on a VPS, cron `0 3 * * *` runs `run.sh` (docker run, append to log, push log to the `logs` branch with a repo-scoped deploy key).
Logs: https://github.com/Minhman23/ds-sync-x7q/blob/logs/sync.log (raw: https://raw.githubusercontent.com/Minhman23/ds-sync-x7q/logs/sync.log)
Each run prints `added/updated/skipped/failed`; a re-run with no changes gives `added=0 updated=0 skipped=414`.

## Sample answer
Chat UI: the last step of `./start.sh` (local only, the API key stays server-side). AI Studio has no way to attach a File Search store in its UI, and without the store the model invents links, so the bot is exercised through the same API call used by `ask.py`.
Known limits: articles removed from the help center are not deleted from the store; chunk count is an estimate (Gemini does not return it).

![sanity check](docs/sanity-check.png)
