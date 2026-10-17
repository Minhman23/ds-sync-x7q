#!/bin/sh
# One command: build, sync the help center into Gemini File Search, then serve the chat UI on http://127.0.0.1:8000
set -e
cd "$(dirname "$0")"
if ! grep -q '^GEMINI_API_KEY=.\{20,\}' .env 2>/dev/null; then
  [ -f .env ] || cp .env.sample .env
  echo "Put your GEMINI_API_KEY in .env (https://aistudio.google.com/apikey), then run ./start.sh again."
  exit 1
fi
docker build -q -t ds-sync-x7q . >/dev/null
docker run --rm --env-file .env -v "$PWD/out:/app/out" ds-sync-x7q || echo "Sync finished with failures; they are retried on the next run."
echo "Chat UI: http://127.0.0.1:8000  (Ctrl+C to stop)"
docker run --rm -it --env-file .env -e HOST=0.0.0.0 -p 127.0.0.1:8000:8000 ds-sync-x7q python chat.py
