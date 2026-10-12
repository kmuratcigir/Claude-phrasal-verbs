#!/usr/bin/env python3
"""
Update the vocabulary tracker (meta/vocab_tracker) from one checked session.

- Every verified vocab-file come-up in session_doc.json (vocab.comeups) adds the
  session date to that row's `dates` (days used unprompted). One date per row per day.
- Every word in drilled_words.txt (this chat's vocab session) counts as one review:
  practice.count +1 and practice.last = date, once per day. Drilled uses never go
  into `dates`: story and quiz uses are practice, not unprompted use.
- Drilled phrasal verbs (study-list items living in meta/pv_tracker since 27.09.26) are
  recorded the same way on their pv row's `practice`, in the pv tracker file given as the
  last argument (the pv_apply.py output), which is rewritten in place.
- Rows are never added here. Only Murat adds words to his list.

Stages use the phrasal verb tracker's rules on the number of different days used:
0 Not Yet Observed, 1-2 Emerging, 3-5 In Progress, 6+ Activated.
`mastered` is Murat's own label and is never changed here.

Usage: python3 vt_apply.py vocab_tracker.json session_doc.json DD.MM.YYYY out.json [drilled_words.txt] [pv_tracker_out.json]
"""
import json, os, sys

def stage(n):
    return "Not Yet Observed" if n == 0 else "Emerging" if n <= 2 else "In Progress" if n <= 5 else "Activated"

def dkey(d):
    a, b, c = d.split("."); return c + b + a

def main(tr_path, sess_path, date, out, drilled_path=None, pv_path=None):
    tr = json.load(open(tr_path)); tr = tr.get("data", tr)
    s = json.load(open(sess_path)); s = s.get("data", s)
    rows = tr["rows"]; by_id = {r["id"]: r for r in rows}
    by_expr = {r["expr"].strip().lower(): r for r in rows}
    pv = None
    if pv_path and os.path.exists(pv_path):
        pv = json.load(open(pv_path)); pv = pv.get("data", pv)
    by_pv = {r["word"].strip().lower(): r for r in (pv or {}).get("rows", [])}
    changes, stageups, missing = [], [], []
    for cu in (s.get("vocab") or {}).get("comeups", []):
        r = by_id.get(cu["id"])
        if not r: missing.append(f'come-up id {cu["id"]} {cu.get("expr")}'); continue
        before = stage(len(r["dates"]))
        if date not in r["dates"]:
            r["dates"].append(date); r["dates"].sort(key=dkey)
            changes.append(f'used: #{r["id"]} {r["expr"]}')
            after = stage(len(r["dates"]))
            if after != before: stageups.append(f'#{r["id"]} {r["expr"]} -> {after}' + (" (Mastered)" if r.get("mastered") else ""))
    if drilled_path and os.path.exists(drilled_path):
        for w in (l.strip() for l in open(drilled_path, encoding="utf-8")):
            if not w: continue
            r = by_expr.get(w.lower())
            label = f'#{r["id"]} {r["expr"]}' if r else None
            if not r and w.lower() in by_pv:
                r = by_pv[w.lower()]; label = f'phrasal verb: {r["word"]}'
            if not r: missing.append(f'drilled word not on either list: {w}'); continue
            p = r.setdefault("practice", {"count": 0, "last": None})
            if p.get("last") != date:
                p["count"] = p.get("count", 0) + 1; p["last"] = date
                changes.append(f'practised: {label}')
    tr["as_of"] = date
    json.dump(tr, open(out, "w"), ensure_ascii=False, indent=1)
    if pv is not None:
        json.dump(pv, open(pv_path, "w"), ensure_ascii=False)
    print(f"{len(changes)} changes")
    for c in changes: print(" ", c)
    print("STAGE-UPS:", "; ".join(stageups) or "none")
    if missing: print("CHECK:", "; ".join(missing))
    n = {}
    for r in rows:
        k = "Mastered" if r.get("mastered") else stage(len(r["dates"]))
        n[k] = n.get(k, 0) + 1
    print("counts:", n)

if __name__ == "__main__":
    main(*sys.argv[1:])
