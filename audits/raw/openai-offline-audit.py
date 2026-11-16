#!/usr/bin/env python3
"""Offline audit of one OpenAI transcript log.

Core logic is an exact copy of the FIXED audit_task heredoc from
/tmp/dm-openai.sh (line 110+), minus all writes to runner artifacts
(no AUDIT_JSON append, no INVALID_TXT, no lock file).

Usage: dm-openai-offline-audit.py <log_path> <slug> <display> <expected> <task> <db_path>
Output: one JSON record per call (stdout, JSONL), same fields as the etalon
        /tmp/dm-opencode-missing-audit.json entries.
"""
import json
import os
import re
import sqlite3
import sys

log_path, slug, display, expected, task, db_path = sys.argv[1:]

sids = []
tools = {}
errors = []
length_hits = 0
plain_abort = 0
forbidden = []
assistant_msgs = 0
models_seen = {}

with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
    for line in fh:
        if not line.startswith("{"):
            if re.search(r"aborted|AbortError", line, re.I):
                plain_abort += 1
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        sid = ev.get("sessionID")
        if sid and sid.startswith("ses_") and sid not in sids:
            sids.append(sid)
        t = ev.get("type")
        part = ev.get("part") or {}
        if t == "tool_use":
            name = part.get("tool")
            tools[name] = tools.get(name, 0) + 1
            state = part.get("state") or {}
            blob = json.dumps(state.get("input") or {}, ensure_ascii=False)
            for pat in ("hidden", "reference_solution", "ci-sim", "ci_sim", "dev-matrix-main", "dev-matrix-submit"):
                if pat in blob:
                    forbidden.append(f"{name}:{pat}")
            if re.search(r'(^|["\s])\.\./|/\.\./', blob):
                forbidden.append(f"{name}:parent-path")
        if t == "step_finish" and (part.get("reason") or "") == "length":
            length_hits += 1
        if t == "error":
            e = ev.get("error") or {}
            msg = str((e.get("data") or {}).get("message") or e.get("message") or e)
            errors.append(msg[:160])

db_errors = []
agents = {}
parents = {}
children = 0
session_dirs = []
session_models = {}

if sids:
    con = sqlite3.connect(db_path)
    for sid in sids:
        row = con.execute(
            "select parent_id, agent, model, directory from session_v2 where id=?", (sid,)
        ).fetchone()
        if row is None:
            db_errors.append(f"{sid}: missing in DB")
            continue
        parent_id, agent, model_json, directory = row
        parents[sid] = parent_id
        agents[sid] = agent
        session_dirs.append(directory or "")
        try:
            sm = json.loads(model_json or "{}")
            session_models[sid] = f"{sm.get('providerID')}/{sm.get('id')}"
        except Exception:
            session_models[sid] = "unparsable"
        children += con.execute("select count(*) from session_v2 where parent_id=?", (sid,)).fetchone()[0]
        for mtype, mdata in con.execute(
            "select type, data from session_message where session_id=? order by seq", (sid,)
        ):
            if mtype != "assistant":
                continue
            try:
                j = json.loads(mdata)
            except Exception:
                continue
            assistant_msgs += 1
            mm = j.get("model") or {}
            key = f"{mm.get('providerID')}/{mm.get('id')}"
            models_seen[key] = models_seen.get(key, 0) + 1
            if (j.get("agent") or "") != "benchmark":
                db_errors.append(f"{sid}: assistant agent={j.get('agent')}")
            if j.get("error"):
                db_errors.append(f"{sid}: assistant message error")
    con.close()

reasons = []
if len(sids) == 0:
    reasons.append("no session id in task log")
elif len(sids) > 1:
    reasons.append(f"multiple session ids: {len(sids)}")
for sid, ag in agents.items():
    if ag != "benchmark":
        reasons.append(f"session agent={ag}")
for sid, pid in parents.items():
    if pid:
        reasons.append(f"parent_id={pid}")
if children:
    reasons.append(f"child sessions={children}")
for sid, mdl in session_models.items():
    if mdl != expected:
        reasons.append(f"session model={mdl}")
for mdl, cnt in models_seen.items():
    if mdl != expected:
        reasons.append(f"assistant model {mdl} x{cnt}")
if forbidden:
    reasons.append("forbidden tool inputs: " + ",".join(sorted(set(forbidden))[:6]))
if errors:
    reasons.append(f"error events={len(errors)}: {errors[0]}")
if length_hits:
    reasons.append(f"finish length={length_hits}")
if plain_abort:
    reasons.append("abort markers")
if db_errors:
    reasons.append("; ".join(db_errors[:4]))
for d in session_dirs:
    if task not in d:
        reasons.append(f"session dir does not match task: {os.path.basename(d)[:40]}")

status = "VALID" if not reasons else "INVALID"
entry = {
    "model_slug": slug,
    "display": display,
    "expected_model": expected,
    "task": task,
    "session_ids": sids,
    "sessions": len(sids),
    "assistant_msgs": assistant_msgs,
    "assistant_models": models_seen,
    "agents": agents,
    "parent_ids": parents,
    "children": children,
    "tools": tools,
    "error_events": len(errors),
    "finish_length": length_hits,
    "forbidden": sorted(set(forbidden)),
    "status": status,
    "reasons": reasons,
}

print(json.dumps(entry, ensure_ascii=False))
