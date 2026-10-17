"""Ask the bot via Gemini + File Search. CLI: python ask.py "How do I add a YouTube video?" (also used by chat.py)."""
import functools
import os
import sys
import time

from google import genai
from google.genai import types

SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""
ARTICLE_BASE = "https://support.optisigns.com/hc/en-us/articles/"

client = genai.Client(http_options=types.HttpOptions(timeout=60_000))  # keep a reference: a temporary client gets closed by GC mid-request


def answer(question):
    for attempt in range(3):  # Gemini returns transient 503s under load
        try:
            r = _generate(question)
            break
        except genai.errors.ServerError:
            if attempt == 2:
                raise
            time.sleep(3)
    gm = r.candidates[0].grounding_metadata
    return _format(r, gm)


def _generate(question):
    return client.models.generate_content(
        model=os.getenv("MODEL", "gemini-3.5-flash-lite"),
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[types.Tool(file_search=types.FileSearch(file_search_store_names=[_store()]))],
        ),
    )


@functools.cache
def _store():
    # Same lookup as main.py, but never creates: an empty store would answer nothing.
    if name := os.getenv("FILE_SEARCH_STORE"):
        return name
    display = os.getenv("STORE_DISPLAY_NAME", "optibot-kb")
    for s in client.file_search_stores.list():
        if s.display_name == display:
            return s.name
    sys.exit(f"No File Search store named {display!r}: run main.py first")


def _format(r, gm):
    # Citations come from the retrieved chunks (file title = article slug), never from model-written URLs.
    titles = dict.fromkeys(c.retrieved_context.title for c in (gm.grounding_chunks if gm else None) or [] if c.retrieved_context)
    urls = [ARTICLE_BASE + t.removesuffix(".md") for t in list(titles)[:3]]
    text = "\n".join(l for l in r.text.splitlines() if not l.startswith("Article URL:"))  # drop model-written ones; keep only verified
    return text.rstrip() + "".join(f"\nArticle URL: {u}" for u in urls)


if __name__ == "__main__":
    print(answer(sys.argv[1] if len(sys.argv) > 1 else "How do I add a YouTube video?"))
