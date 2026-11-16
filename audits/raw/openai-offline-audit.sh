#!/usr/bin/env bash
# Offline audit of OpenAI queue transcripts (post-fix of the models_seen bug).
# 3 valid models x 13 tasks = 39 audits. READ-ONLY wrt runner artifacts:
# does NOT write dm-openai*.json / invalid.txt, no runners launched, no DB writes.
set -uo pipefail

PY=/Users/gogelgans/Documents/Work/dev-matrix-main/.venv/bin/python
DB=/Users/gogelgans/.local/share/opencode/opencode.db
DRIVER=/tmp/dm-openai-offline-audit.py
RECS=/tmp/dm-openai-audit-fixed.jsonl
OUT_JSON=/tmp/dm-openai-audit-fixed.json
OUT_LOG=/tmp/dm-openai-audit-fixed.log

MODELS=(
  "gpt-6.1-terra|GPT-6.1 Terra|openai/gpt-6.1-terra"
  "gpt-6.1-sol|GPT-6.1 Sol|openai/gpt-6.1-sol"
  "gpt-6-luna|GPT-6 Luna|openai/gpt-6-luna"
)

TASKS=(
  sec-01-clock-skew
  obs-02-query-redactor
  algo-03-range-merger
  arch-04-tag-registry
  infra-05-k8s-pod-admission
  onec-06-payment-allocator
  auth-07-claim-roles
  host-08-host-header-guard
  scrub-09-metadata-scrubber
  flag-10-feature-flag-router
  tenant-11-scoped-listing
  authz-12-uniform-404
  idem-13-idempotent-signup
)

: > "$RECS"
total=0
failed=0
for ms in "${MODELS[@]}"; do
  IFS='|' read -r slug disp id <<< "$ms"
  for t in "${TASKS[@]}"; do
    tlog="/tmp/dm-openai-${slug}-${t}.log"
    if [ ! -f "$tlog" ]; then
      echo "MISSING LOG: $tlog" >> "$OUT_LOG"
      failed=$((failed+1))
      continue
    fi
    if ! "$PY" "$DRIVER" "$tlog" "$slug" "$disp" "$id" "$t" "$DB" >> "$RECS"; then
      echo "DRIVER ERROR: $tlog" >> "$OUT_LOG"
      failed=$((failed+1))
      continue
    fi
    total=$((total+1))
  done
done

# Build final JSON array + AUDIT log lines from the collected JSONL records.
"$PY" - "$RECS" "$OUT_JSON" "$OUT_LOG" <<'PY2'
import json, sys
recs_path, out_json, out_log = sys.argv[1:]
data = []
with open(recs_path, "r", encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if line:
            data.append(json.loads(line))
with open(out_json, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
with open(out_log, "a", encoding="utf-8") as fh:
    for e in data:
        rs = "; ".join(e["reasons"]) or "-"
        fh.write(f"AUDIT {e['model_slug']} {e['task']}: {e['status']} "
                 f"sessions={e['sessions']} msgs={e['assistant_msgs']} reasons={rs}\n")
PY2

echo "TOTAL_AUDITS=$total FAILED_CALLS=$failed"
echo "OUT_JSON=$OUT_JSON"
echo "OUT_LOG=$OUT_LOG"
