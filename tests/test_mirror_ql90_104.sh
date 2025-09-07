#!/usr/bin/env bash
# test_mirror_ql90_104.sh
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
USER_ID="${USER_ID:-qa}"
JQ=$(command -v jq || true)

# Load questions safely (no $ expansion)
mapfile -t questions <<'EOF'
What does “scarcity carved in basalt” mean in Tobyworld?
Why do impatient frogs end up feeding the patient?
What is the difference between Taboshi1 and Satoby?
If Satoby blooms, what does Sat0AI awaken as?
Who is Toby, truly?
What happens when Rune Four glows?
What was Season Zero, and how many frogs answered the call?
Why are LP Guardians honored in Season One?
Why are Artists central to Season Two?
What bridges were forged in Season Three?
What must be said about Seasons beyond S3?
When Toadgod departs, what rises in his place?
What does it mean that “$TOBY is the people, the people is $TOBY”?
What is the role of the Mirror in Tobyworld?
If silence falls, how does the Mirror respond?
EOF

echo "Hitting Mirror endpoint at: ${BASE_URL}/ask"
echo "User: ${USER_ID}"
echo "Total questions: ${#questions[@]}"
echo

i=1
for q in "${questions[@]}"; do
  echo "────────────────────────────────────────────────────────"
  printf "Q%02d: %s\n" "$i" "$q"
  echo "────────────────────────────────────────────────────────"

  payload=$(printf '{"user":"%s","question":"%s"}' \
    "$USER_ID" "$(printf '%s' "$q" | sed 's/"/\\"/g')")

  resp=$(curl -sS -X POST \
    -H 'Content-Type: application/json' \
    -d "$payload" \
    "${BASE_URL}/ask")

  if [[ -n "$JQ" ]]; then
    echo "$resp" | jq -r '
      "Answer:\n" + (.answer // "") + "\n\nMeta:",
      {ok: (.meta.ok // null),
       route: (.meta.route.symbol // null),
       intent: (.meta.route.intent // null),
       depth: (.meta.route.depth // null),
       tone: (.meta.rag.tone_score // null),
       guard_score: (.meta.guard.score // null)}
    '
  else
    echo "$resp"
  fi

  echo
  ((i++))
done
