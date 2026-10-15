#!/bin/sh
# One daily run (cron). Appends to logs/sync.log, then publishes it to the `logs` branch if ./logs-repo exists.
cd "$(dirname "$0")" || exit 1
mkdir -p logs
echo "=== run $(date -u +%FT%TZ) ===" >> logs/sync.log
docker run --rm --env-file .env ds-sync-x7q >> logs/sync.log 2>&1
echo "exit=$?" >> logs/sync.log
if [ -d logs-repo/.git ]; then
  cp logs/sync.log logs-repo/sync.log
  git -C logs-repo add sync.log && git -C logs-repo commit -qm "run $(date -u +%FT%TZ)" && git -C logs-repo push -q origin logs
fi
