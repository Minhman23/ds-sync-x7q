"""Sanity check: ask the bot via Gemini + File Search. Usage: python ask.py "How do I add a YouTube video?" """
import os
import sys

from google import genai
from google.genai import types

SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""

client = genai.Client(http_options=types.HttpOptions(timeout=60_000))  # keep a reference: a temporary client gets closed by GC mid-request
r = client.models.generate_content(
    model=os.getenv("MODEL", "gemini-3.5-flash"),
    contents=sys.argv[1] if len(sys.argv) > 1 else "How do I add a YouTube video?",
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(file_search=types.FileSearch(file_search_store_names=[os.environ["FILE_SEARCH_STORE"]]))],
    ),
)
print(r.text)
gm = r.candidates[0].grounding_metadata
for c in (gm.grounding_chunks if gm else None) or []:
    print("source:", c.retrieved_context.title if c.retrieved_context else c)
