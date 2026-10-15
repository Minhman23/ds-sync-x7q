"""Daily job: scrape Zendesk help center -> Markdown -> sync delta to a Gemini File Search store.

Stateless: article id + content hash live in each document's `custom_metadata`,
so the job needs no volume/DB and can run on any ephemeral container.
"""
import hashlib
import logging
import math
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from markdownify import markdownify

BASE = os.getenv("HELP_CENTER_BASE", "https://support.optisigns.com")
LOCALE = "en-us"
OUT_DIR = Path(os.getenv("OUT_DIR", "out"))
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", "0"))  # 0 = all
CHUNK_MAX, CHUNK_OVERLAP = 500, 50  # whitespace chunking; API caps max_tokens_per_chunk at 512
DRY_RUN = os.getenv("DRY_RUN") == "1"  # scrape only, no Gemini calls

log = logging.getLogger("job")


def fetch_articles():
    url = f"{BASE}/api/v2/help_center/{LOCALE}/articles.json?per_page=100"
    arts = []
    while url:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        d = r.json()
        arts += [a for a in d["articles"] if not a["draft"]]
        url = d["next_page"]
    return arts[:MAX_ARTICLES] if MAX_ARTICLES else arts


def to_markdown(a):
    md = markdownify(a["body"] or "", heading_style="ATX", code_language="", strip=["script", "style"])
    md = re.sub(r"^(#{1,6}) \*\*(.+?)\*\*\s*$", r"\1 \2", md, flags=re.M)  # "## **Title**" -> "## Title"
    md = re.sub(r"^\|\s*\|\n\| --- \|\n", "", md, flags=re.M)  # single-column tables render an empty header row
    md = re.sub(r"!\[[^\]]*\]\(data:[^)]*\)", "", md)  # inline base64 images (one is 125 KB) are noise and break upload
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    # Article URL line first: the system prompt asks the bot to cite "Article URL:" lines.
    return f"# {a['title']}\n\nArticle URL: {a['html_url']}\n\n{md}\n"


def slug(a):
    return a["html_url"].rsplit("/", 1)[-1]  # "<id>-<title-slug>", unique + stable


def scrape():
    OUT_DIR.mkdir(exist_ok=True)
    items = []
    for a in fetch_articles():
        md = to_markdown(a)
        path = OUT_DIR / f"{slug(a)}.md"
        path.write_text(md, encoding="utf-8")
        items.append({"id": str(a["id"]), "path": path, "hash": hashlib.sha256(md.encode()).hexdigest()})
    log.info("scraped %d articles -> %s", len(items), OUT_DIR)
    return items


def est_chunks(path):
    tokens = len(path.read_text(encoding="utf-8")) / 4  # ~4 chars/token; Gemini doesn't expose chunk counts
    return max(1, math.ceil((tokens - CHUNK_OVERLAP) / (CHUNK_MAX - CHUNK_OVERLAP)))


def get_or_create_store(client):
    if name := os.getenv("FILE_SEARCH_STORE"):
        return client.file_search_stores.get(name=name)
    display = os.getenv("STORE_DISPLAY_NAME", "optibot-kb")
    for s in client.file_search_stores.list():
        if s.display_name == display:
            return s
    return client.file_search_stores.create(config={"display_name": display})


def remote_state(client, store):
    """{article_id: (document_name, hash)} from document custom_metadata."""
    state = {}
    for d in client.file_search_stores.documents.list(parent=store.name):
        meta = {m.key: m.string_value for m in (d.custom_metadata or [])}
        if "article_id" in meta:
            state[meta["article_id"]] = (d.name, meta.get("hash"))
    return state


def upload(client, store, it):
    op = client.file_search_stores.upload_to_file_search_store(
        file_search_store_name=store.name,
        file=it["path"],
        config={
            "display_name": it["path"].name,
            "mime_type": "text/markdown",
            "custom_metadata": [
                {"key": "article_id", "string_value": it["id"]},
                {"key": "hash", "string_value": it["hash"]},
            ],
            "chunking_config": {
                "white_space_config": {"max_tokens_per_chunk": CHUNK_MAX, "max_overlap_tokens": CHUNK_OVERLAP}
            },
        },
    )
    while not op.done:
        time.sleep(2)
        op = client.operations.get(op)
    if op.error:
        raise RuntimeError(f"upload failed for {it['path'].name}: {op.error}")


def sync(items):
    from google import genai

    client = genai.Client()
    store = get_or_create_store(client)
    remote = remote_state(client, store)
    added = [i for i in items if i["id"] not in remote]
    updated = [i for i in items if i["id"] in remote and remote[i["id"]][1] != i["hash"]]
    skipped = len(items) - len(added) - len(updated)

    def work(it):
        for attempt in range(3):  # Gemini returns transient 503s under load
            try:
                upload(client, store, it)  # upload first so the article is never missing from the store
                if old := remote.get(it["id"]):
                    client.file_search_stores.documents.delete(name=old[0], config={"force": True})
                return est_chunks(it["path"])
            except Exception as e:
                log.warning("%s attempt %d failed: %s", it["path"].name, attempt + 1, str(e)[:200])
                time.sleep(5 * (attempt + 1))
        return None  # stays in the delta, retried on the next run

    todo = added + updated
    with ThreadPoolExecutor(max_workers=int(os.getenv("WORKERS", "4"))) as ex:
        results = list(ex.map(work, todo))
    ok = [c for c in results if c is not None]
    failed = len(results) - len(ok)
    log.info("store=%s added=%d updated=%d skipped=%d failed=%d files_embedded=%d est_chunks=%d",
             store.name, len(added), len(updated), skipped, failed, len(ok), sum(ok))
    return failed


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    items = scrape()
    if DRY_RUN:
        log.info("DRY_RUN=1: skipping upload")
        return 0
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        log.error("GEMINI_API_KEY not set")
        return 1
    return 1 if sync(items) else 0


if __name__ == "__main__":
    sys.exit(main())
