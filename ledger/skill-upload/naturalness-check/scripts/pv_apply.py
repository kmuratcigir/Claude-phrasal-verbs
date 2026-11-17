#!/usr/bin/env python3
"""
Apply one checked session to the phrasal verb tracker stored in the ledger
(meta/pv_tracker). Adds the session date to every tracker word that came up,
adds first-time words with that date, and appends any notes. One date per word
per day, so re-running the check in the same chat changes nothing twice.

Stage, recency and signal are NOT stored: the ledger page and the .docx export
work them out from the dates, so they are always current.

Usage: python3 pv_apply.py meta/pv_tracker.json session_doc.json <DD.MM.YYYY> pv_tracker_out.json
"""
import json, sys
from datetime import datetime

def d(s): return datetime.strptime(s, "%d.%m.%Y")

def main(tpath, spath, date, out):
    doc = json.load(open(tpath)); p = json.load(open(spath)).get("pv")
    if not p: print("session has no phrasal verb data; tracker unchanged"); json.dump(doc, open(out, "w"), ensure_ascii=False); return
    rows = doc["rows"]; by = {r["word"]: r for r in rows}
    before = {r["word"]: len(set(r["dates"])) for r in rows}
    changes = []
    for w in p["comeups"]:
        r = by[w]
        if date not in r["dates"]: r["dates"].append(date); changes.append(f"come-up: {w}")
    for w in p["new_words"]:
        if w in by:
            if date not in by[w]["dates"]: by[w]["dates"].append(date); changes.append(f"come-up: {w}")
            continue
        r = {"word": w, "dates": [date], "notes": ""}
        rows.append(r); by[w] = r; changes.append(f"new word: {w}")
    for w, note in p.get("notes", {}).items():
        if w in by and note and note not in by[w]["notes"]:
            by[w]["notes"] = (by[w]["notes"] + f" {date[:5]}: {note}").strip()
    for r in rows: r["dates"] = sorted(set(r["dates"]), key=d)
    stage = lambda n: "Activated" if n >= 6 else "In Progress" if n >= 3 else "Emerging" if n else "Not Yet Observed"
    ups = [f'{r["word"]} -> {stage(len(r["dates"]))}' for r in rows
           if r["word"] in before and stage(len(r["dates"])) != stage(before[r["word"]])]
    doc["as_of"] = date
    json.dump(doc, open(out, "w"), ensure_ascii=False)
    print(json.dumps({"changes": changes, "stage_ups": ups, "total_words": len(rows)}, indent=1))

if __name__ == "__main__":
    main(*sys.argv[1:5])
