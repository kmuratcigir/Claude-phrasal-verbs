#!/usr/bin/env python3
"""
Overview tab (added 30.09.26): the numbers behind the brief, and the check that the brief
and the day's report are complete before they are saved.

  stats  : prints the figures Claude writes the brief from: today vs the session before,
           this week (Monday to Sunday) vs last week, the last 3 sessions vs the first 3,
           and the mistakes by impact (m = changes the meaning, f = sounds foreign, s = slip).
           Every number in the brief must come from this output or from session_doc.json.
  finish : checks overview_draft.json (shape, lengths, impact labels) and report.md, puts
           the report text into session_doc.json as "report", and writes overview_out.json
           for meta/overview. Stops without writing anything if something is missing.

Usage:
  python3 overview.py stats  <sessions_dir> session_doc.json <doc_id>
  python3 overview.py finish <sessions_dir> session_doc.json <doc_id> overview_draft.json report.md overview_out.json

sessions_dir holds the ledger's session docs (ArtifactData list sessions with out_dir); this
chat's session_doc.json replaces its own older copy there, so a rerun counts it once.
"""
import glob, json, os, sys
from datetime import date as Date

def load(p):
    d = json.load(open(p, encoding="utf-8")); return d.get("data", d)

def dkey(s):
    d, m, y = s.split("."); return Date(int(y), int(m), int(d))

def sessions(sdir, sess_path, doc_id):
    docs = {}
    for p in glob.glob(os.path.join(sdir, "*.json")):
        docs[os.path.splitext(os.path.basename(p))[0]] = load(p)
    docs[doc_id] = load(sess_path)
    out = sorted(docs.items(), key=lambda kv: (dkey(kv[1]["date"]), kv[0]))
    return [dict(v, _id=k) for k, v in out]

def agg(ss):
    """Word-weighted figures for a group of sessions (None when there is nothing to measure)."""
    if not ss: return None
    vw = sum(s["by_mode"]["voice"]["words"] for s in ss)
    ve = sum(s["by_mode"]["voice"]["errors"] for s in ss)
    iv = sum(((s.get("interference") or {}).get("by_mode") or {}).get("voice", {}).get("count", 0) for s in ss)
    w = sum(s["words"] for s in ss)
    b2 = sum((s.get("vocab") or {}).get("b2plus_share", 0) * s["words"] for s in ss)
    pvs = [s for s in ss if (s.get("pv") or {}).get("instances")]
    pvw, pvi = sum(s["words"] for s in pvs), sum(s["pv"]["instances"] for s in pvs)
    cu = [len((s.get("vocab") or {}).get("comeups", [])) for s in ss]
    imp = {"m": 0, "f": 0, "s": 0}
    for s in ss:
        for e in s.get("errors", []):
            if e.get("impact") in imp: imp[e["impact"]] += 1
    n_imp = sum(imp.values())
    r = lambda x, d=2: round(x, d)
    return {
        "sessions": len(ss), "words": w, "voice_words": vw,
        "errors_per_100_voice": r(ve / vw * 100) if vw else None,
        "interference_per_100_voice": r(iv / vw * 100) if vw else None,
        "b2plus_share": r(b2 / w, 2) if w else None,
        "pv_one_per": round(pvw / pvi) if pvi else None,
        "list_comeups_per_session": r(sum(cu) / len(cu), 1),
        "impact": imp,
        "meaning_share_pct": round(imp["m"] / n_imp * 100) if n_imp else None,
    }

def weeks(ss):
    last = dkey(ss[-1]["date"]); y, wk, _ = last.isocalendar()
    this = [s for s in ss if dkey(s["date"]).isocalendar()[:2] == (y, wk)]
    prev_monday = Date.fromordinal(last.toordinal() - last.weekday() - 7)
    pw = prev_monday.isocalendar()[:2]
    lastw = [s for s in ss if dkey(s["date"]).isocalendar()[:2] == pw]
    return this, lastw

def stats(sdir, sess_path, doc_id):
    ss = sessions(sdir, sess_path, doc_id)
    this, lastw = weeks(ss)
    blocks = {
        "today": (ss[-1:], ss[-2:-1]),
        "this_week_vs_last_week": (this, lastw),
        "last3_vs_first3": (ss[-3:], ss[:3]),
    }
    out = {"sessions": [f'{s["date"]} {s["_id"]} {s["words"]} words' for s in ss],
           "all_sessions": agg(ss)}
    for k, (a, b) in blocks.items():
        out[k] = {"now": agg(a), "before": agg(b),
                  "now_dates": [s["date"] for s in a], "before_dates": [s["date"] for s in b]}
    labelled = [s for s in ss if any("impact" in e for e in s.get("errors", []))]
    out["impact_by_session"] = [{"date": s["date"], **agg([s])["impact"]} for s in labelled]
    missing = [s["date"] for s in ss if s.get("errors") and not any("impact" in e for e in s["errors"])]
    if missing: out["sessions_without_impact_labels"] = missing
    print(json.dumps(out, indent=1, ensure_ascii=False))

# ---------------------------------------------------------------- finish
MOVES = {"better", "worse", "same", "best", "worst"}
IMPACTS = {"m", "f", "s"}

def words(s): return len(str(s).split())

def check_draft(d):
    probs = []
    need = lambda cond, msg: None if cond else probs.append(msg)
    need(isinstance(d.get("headline"), str) and 3 <= words(d["headline"]) <= 16, "headline: one or two short sentences (3-16 words)")
    need(isinstance(d.get("intro"), str) and 10 <= words(d["intro"]) <= 60, "intro: 10-60 words")
    per = d.get("periods") or {}
    for k in ("today", "week", "start"):
        p = per.get(k)
        if not isinstance(p, dict): probs.append(f"periods.{k} missing"); continue
        need(isinstance(p.get("sub"), str) and p["sub"], f"periods.{k}.sub missing (dates, words)")
        need(isinstance(p.get("verdict"), str) and 2 <= words(p["verdict"]) <= 10, f"periods.{k}.verdict: 2-10 words")
        sc = p.get("scores") or []
        need(2 <= len(sc) <= 4, f"periods.{k}.scores: 2-4 lines")
        for i, s in enumerate(sc):
            need(all(s.get(x) not in (None, "") for x in ("label", "value")) and s.get("move") in MOVES,
                 f"periods.{k}.scores[{i}]: label, value and move ({'/'.join(sorted(MOVES))}) needed")
        pts = p.get("points") or []
        need(2 <= len(pts) <= 5, f"periods.{k}.points: 2-5 points")
        need(any(x.get("kind") == "good" for x in pts) and any(x.get("kind") == "bad" for x in pts),
             f"periods.{k}.points: at least one good and one bad (frank both ways)")
        for i, x in enumerate(pts):
            need(x.get("kind") in ("good", "bad") and x.get("text") and words(x["text"]) <= 40,
                 f"periods.{k}.points[{i}]: kind good/bad and text of at most 40 words")
    pr = d.get("priorities") or []
    need(len(pr) == 3, "priorities: exactly 3")
    for i, x in enumerate(pr):
        need(x.get("title") and x.get("text") and x.get("impact") in IMPACTS and x.get("said") and x.get("say"),
             f"priorities[{i}]: title, text, impact (m/f/s), said and say needed")
    notes = d.get("impact_notes") or {}
    for k in ("latest", "all", "trend"):
        need(isinstance(notes.get(k), str) and 8 <= words(notes[k]) <= 60, f"impact_notes.{k}: 8-60 words")
    bm = d.get("best_moments") or []
    need(1 <= len(bm) <= 8, "best_moments: 1-8 items")
    for i, x in enumerate(bm):
        need(x.get("title") and x.get("date") and (x.get("quote") or x.get("sub")),
             f"best_moments[{i}]: title, date and a quote or sub line")
    return probs

def check_report(txt):
    probs = []
    if len(txt.split()) < 120: probs.append("report.md looks too short (under 120 words)")
    for h in ("## Errors", "## Strong B2+ grammar", "## Phrasal verbs", "## Vocabulary", "## Turkish interference"):
        if h not in txt: probs.append(f'report.md: section "{h}" missing')
    return probs

def finish(sdir, sess_path, doc_id, draft_path, report_path, out):
    d = json.load(open(draft_path, encoding="utf-8"))
    rep = open(report_path, encoding="utf-8").read().strip()
    doc = load(sess_path)
    probs = check_draft(d) + check_report(rep)
    unl = [e for e in doc.get("errors", []) if e.get("impact") not in IMPACTS]
    if unl: probs.append(f"{len(unl)} error(s) in session_doc.json have no impact label (rerun session.py with them)")
    if probs:
        print("STOP: nothing written. Fix these and rerun:")
        for p in probs: print("  -", p)
        sys.exit(1)
    doc["report"] = rep
    json.dump(doc, open(sess_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    ss = sessions(sdir, sess_path, doc_id)
    o = dict(d)
    o.update({"as_of": doc["date"], "session": doc_id, "sessions_covered": len(ss),
              "words_covered": sum(s["words"] for s in ss), "written_by": "Claude, naturalness check"})
    json.dump(o, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"overview ready: {out} (as of {doc['date']}, {len(ss)} sessions, {o['words_covered']} words) · "
          f"report added to {sess_path} ({len(rep.split())} words)")

if __name__ == "__main__":
    mode = sys.argv[1]
    {"stats": stats, "finish": finish}[mode](*sys.argv[2:])
