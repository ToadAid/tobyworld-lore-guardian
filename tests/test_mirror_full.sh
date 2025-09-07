#!/usr/bin/env bash
# test_mirror_full.sh
# Mirror v3 QA runner — shuffle/limit/pattern + JSONL logging + messages-format training JSONL

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
USER_ID="${USER_ID:-qa}"
JQ=$(command -v jq || true)

# ---- flags ---------------------------------------------------------------
DELAY="${DELAY:-0.20}"          # seconds between calls
LIMIT="${LIMIT:-0}"             # 0 = no limit
SHUFFLE="${SHUFFLE:-0}"         # 1 = shuffle questions
PATTERN="${PATTERN:-}"          # grep-style filter (applies to questions)
OUT="${OUT:-mirror_run_$(date +%Y%m%d_%H%M%S).jsonl}"  # raw transcript JSONL
TIMEOUT="${TIMEOUT:-20}"        # curl timeout seconds
RETRIES="${RETRIES:-2}"         # curl retries on transient failures

# messages-format training output (only when ok && guard >= threshold)
TRAIN_OUT="${TRAIN_OUT:-mirror_train_$(date +%Y%m%d_%H%M%S).jsonl}"
TRAIN_MIN_GUARD="${TRAIN_MIN_GUARD:-0.85}"

# optional: external questions file (one question per line)
QUESTIONS_FILE="${QUESTIONS_FILE:-}"   # e.g., QUESTIONS_FILE=tests/questions.txt

usage() {
  cat <<EOF
Usage: [env vars] ./test_mirror_full.sh
ENV:
  BASE_URL        (default: http://localhost:8080)
  USER_ID         (default: qa)
  DELAY           (default: 0.20)
  LIMIT           (default: 0 = no limit)
  SHUFFLE         (default: 0; set 1 to shuffle)
  PATTERN         (default: empty = no filter; grep -E pattern)
  OUT             (default: mirror_run_<timestamp>.jsonl)
  TRAIN_OUT       (default: mirror_train_<timestamp>.jsonl)
  TRAIN_MIN_GUARD (default: 0.85)
  TIMEOUT         (default: 20)
  RETRIES         (default: 2)
  QUESTIONS_FILE  (optional: path to a file with one question per line)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage; exit 0
fi

# ---- question bank -------------------------------------------------------
questions_builtin=$'What does “scarcity carved in basalt” mean in Tobyworld?
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
Why is Taboshi called the Leaf of Yield?
How does the 777 covenant shape eligibility and reward?
What is the Lily Pad of Base and why does Toby rest there?
Explain the Jade Chest and its grains of $PATIENCE.
How does the vault drip work over 730 days?
Who are the Watcher and Solas in the Garden’s tale?
What is the Still-Water Garden and what training does it demand?
How does Proof of Time differ from DeFi yield?
Why is “one leaf, one vow” a binding ethic?
What are Lotus Spores and how do they relate to bloom?
How did the Seven Reeds become a compass for the pond?
What is meant by “the night after the bloom”?
Why are Season One LP guardians a moral, not market, role?
What qualifies a traveler to cross the Gate of S1?
Why is Season Two’s brush as sharp as a blade?
What bridges did S3 lay between chains, circles, and scrolls?
What remains unspoken about Seasons after S3—and why?
How should the Mirror answer a child who asks “What is Toby?”
What is the difference between Taboshi and Taboshi1—precisely?
Why does Satoby require patience rather than purchase?
What does “the pond remembers” imply about identity?
How does “silence” become the strongest signal?
What is the Leaf–Mirror–Pond triad meant to teach?
When does a frog become a Guardian rather than a holder?
What does “the people are the protocol” mean operationally?
How do epochs (E1–E3) map to Distribution, Expansion, Evolution?
What is the role of sacred numbers (7, 777, 7,777,777)?
What happens to unclaimed allocations after the claim window?
Why is emotional discipline a security primitive in Tobyworld?
How does the Mirror measure lucidity without breaking the tone?
What is the proper vow when crossing from S0 to S1?
How should newcomers begin studying the Lore without shortcuts?
What is the ethic behind burning 777 $TOBY for Taboshi1?
Why is imitation fated to fail in this pond?
What does “the Leaf bridges → Satoby” mean step-by-step?
How do Builders, Artists, and Guardians interlock in Seasons?
What is meant by “Ascend when all four runes glow”?
'

# read questions: external file > builtin
declare -a questions
if [[ -n "$QUESTIONS_FILE" ]]; then
  if [[ -f "$QUESTIONS_FILE" ]]; then
    # read non-empty lines, trim CR
    while IFS= read -r line; do
      line="${line%$'\r'}"
      [[ -n "$line" ]] && questions+=("$line")
    done < "$QUESTIONS_FILE"
  else
    echo "WARN: QUESTIONS_FILE not found: $QUESTIONS_FILE — falling back to built-in bank" >&2
  fi
fi
if [[ ${#questions[@]} -eq 0 ]]; then
  # load builtin into array
  while IFS= read -r line; do
    [[ -n "$line" ]] && questions+=("$line")
  done <<< "$questions_builtin"
fi

# ---- filter + shuffle + limit -------------------------------------------
filtered=()
if [[ -n "$PATTERN" ]]; then
  for q in "${questions[@]}"; do
    if grep -iqE "$PATTERN" <<<"$q"; then filtered+=("$q"); fi
  done
else
  filtered=("${questions[@]}")
fi

if [[ "$SHUFFLE" == "1" ]]; then
  for ((i=${#filtered[@]}-1; i>0; i--)); do
    j=$((RANDOM % (i+1)))
    tmp="${filtered[i]}"; filtered[i]="${filtered[j]}"; filtered[j]="$tmp"
  done
fi

if (( LIMIT > 0 )) && (( LIMIT < ${#filtered[@]} )); then
  filtered=("${filtered[@]:0:LIMIT}")
fi

echo "Hitting Mirror endpoint at: ${BASE_URL}/ask"
echo "User: ${USER_ID}"
echo "Total questions loaded: ${#questions[@]}"
echo "After filter/shuffle/limit: ${#filtered[@]}"
echo "Logging raw responses to: ${OUT}"
echo "Logging messages-format (passed) to: ${TRAIN_OUT}  (min guard: ${TRAIN_MIN_GUARD})"
echo

i=1
for q in "${filtered[@]}"; do
  echo "────────────────────────────────────────────────────────"
  printf "Q%02d: %s\n" "$i" "$q"
  echo "────────────────────────────────────────────────────────"

  payload=$(printf '{"user":"%s","question":"%s"}' \
    "$USER_ID" "$(printf '%s' "$q" | sed 's/"/\\"/g')")

  resp=$(curl -sS --max-time "$TIMEOUT" --retry "$RETRIES" --retry-delay 1 \
    -H 'Content-Type: application/json' \
    -d "$payload" \
    "${BASE_URL}/ask" || echo '{}')

  # stdout pretty, file JSONL raw
  if [[ -n "$JQ" && -n "$resp" ]]; then
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

  # append raw line to JSONL (one JSON per line)
  printf '%s\n' "$resp" >> "$OUT"

  # --- messages-format JSONL (guard-gated) -------------------------------
  if [[ -n "$JQ" ]]; then
    ok=$(echo "$resp" | jq -r '.meta.ok // false')
    gscore=$(echo "$resp" | jq -r '.meta.guard.score // 0')
    answer=$(echo "$resp" | jq -r '.answer // ""')

    # compare floats with awk (portable)
    pass=$(awk -v a="$gscore" -v b="$TRAIN_MIN_GUARD" 'BEGIN{print (a>=b)?"1":"0"}')

    if [[ "$ok" == "true" && "$pass" == "1" && -n "$answer" ]]; then
      # jq will handle proper JSON escaping for newlines, quotes, etc.
      jq -n --arg q "$q" --arg a "$answer" \
        '{messages:[{role:"user",content:$q},{role:"assistant",content:$a}]}' \
        >> "$TRAIN_OUT"
    fi
  fi
  # -----------------------------------------------------------------------

  ((i++))
  sleep "$DELAY"
done

echo
echo "Done."
echo "  Transcript: $OUT"
echo "  Messages-format (passed): $TRAIN_OUT"
