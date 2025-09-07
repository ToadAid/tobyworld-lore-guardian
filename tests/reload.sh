#!/usr/bin/env bash
set -euo pipefail
URL="${URL:-http://127.0.0.1:8080/admin/retriever/rebuild}"
echo "→ Rebuilding retriever from $URL"
curl -s -X POST "$URL" | jq .
