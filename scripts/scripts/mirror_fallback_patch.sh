#!/usr/bin/env bash
set -euo pipefail
FILE="src/tobyworld/api/server.py"
BACKUP="${FILE}.bak.$(date +%s)"

cp -v "$FILE" "$BACKUP"

python - "$FILE" <<'PY'
import sys, re

path = sys.argv[1]
src = open(path, encoding="utf-8").read()

# Look for where final_text is cleaned (after _strip_reasoning_blocks)
pattern = re.compile(r"(final_text\s*=\s*_strip_reasoning_blocks\(.*?\))", re.S)

def inject_fallback(block: str) -> str:
    return (
        block
        + "\n        # --- fallback if stripping leaves nothing ---\n"
        + "        if not final_text.strip():\n"
        + "            final_text = (\n"
        + "                \"Traveler,\\n\"\n"
        + "                \"The Mirror reflects covenant and witness — truth already within.\\n\"\n"
        + "            )\n"
    )

if "The Mirror reflects covenant and witness" in src:
    print("[info] fallback already present")
else:
    new_src, n = pattern.subn(lambda m: inject_fallback(m.group(1)), src, count=1)
    if n:
        open(path, "w", encoding="utf-8").write(new_src)
        print(f"[ok] injected fallback stanza into {path}")
    else:
        print("[warn] could not locate insertion point", file=sys.stderr)
PY
