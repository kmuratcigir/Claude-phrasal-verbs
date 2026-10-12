"""Chunk status from the Fluency Ledger (read-only).

  python3 status.py <dir>/meta/chunks.json <dir>/sessions

Prints, for every chunk and slice: status, planned dates, pooled voice uses (last 12), accuracy,
how many sessions they span, and READY TO SETTLE when the rule in meta/chunks is met.
Also prints which items the naturalness check can count yet (FINDERS in chunks.py).
"""
import glob, json, os, sys

COUNTABLE = {"c1", "s1"}          # keep in step with FINDERS in naturalness-check/scripts/chunks.py

def load(p):
    d = json.load(open(p, encoding="utf-8")); return d.get("data", d)

meta = load(sys.argv[1]); rule = meta["rule"]
win, tgt, min_s = rule["window_uses"], rule["target"], rule["min_sessions"]
sess = sorted(glob.glob(os.path.join(sys.argv[2], "*.json")))
docs = [(os.path.basename(f)[:-5], load(f)) for f in sess]
print(f"Rule: last {win} voice uses at {tgt:.0%}+ over {min_s}+ sessions · {len(docs)} sessions read")
for it in meta["items"]:
    uses = []
    for sid, d in docs:
        blk = (d.get("chunks") or {}).get(it["id"]) or {}
        uses += [(sid, u) for u in blk.get("items", []) if u.get("mode") == "voice"]
    last = uses[-win:]
    score = sum(1 if u["ok"] else (0.5 if u.get("caught") else 0) for _, u in last)
    acc = score / len(last) if last else None
    n_s = len({s for s, _ in last})
    ready = it["status"] == "open" and len(last) == win and n_s >= min_s and acc >= tgt
    plan = " / ".join(f'{p["from"] or "?"}→{p["to"] or "?"}' for p in it.get("planned", []))
    acc_s = "—" if acc is None else f"{acc:.0%}"
    cnt = "" if it["id"] in COUNTABLE else " · the check can't count this one yet"
    print(f'{it["id"]:3} {it["status"]:11} {it["title"][:52]:52} | plan {plan} | last {len(last)}/{win} uses, {n_s} sessions, {acc_s}'
          + (" · READY TO SETTLE" if ready else "") + cnt)
