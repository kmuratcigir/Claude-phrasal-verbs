#!/usr/bin/env python3
"""
Merge detector candidates with Claude's verdicts into one session document
for the Fluency Ledger dashboard (collection "sessions").

verdicts.json (written by Claude after reviewing the REVIEW LIST):
{
  "drop":    [12, 40],                      # false positives, discarded
  "error":   {"57": "it's been started -> it started"},   # use-candidates that were actually wrong (+ fix)
  "fix":     {"3": "despite + clause -> even though ..."},  # optional fix text for detector-flagged errors
  "relabel": {"8": "err_in_the_meantime"},  # move a candidate to another concept id
  "extra":   [ {"concept": "err_preposition", "turn": "T56", "mode": "voice",
                "sentence": "...", "result": "error", "fix": "...", "impact": "f"} ],  # errors the detector missed
  "impact":  {"57": "m"}                    # impact of an error line (30.09.26): m / f / s, see below
}
Defaults: detector "use" -> correct, detector "error" -> error.
Every error must end up with a fix (28.09.26) and an impact label (30.09.26): if any has
none, the script prints them and stops without writing the session. Add them to verdicts.json
and rerun. Impact: m = changes the meaning, f = sounds foreign (meaning clear), s = slip (he
knows the rule; it broke under pressure). DEFAULT_IMPACT covers the fixed types; a label
written in verdicts.json always wins.

Usage: python3 session.py candidates.json verdicts.json <DD.MM.YYYY> "<thread title>" <doc_id> session_doc.json [vocab_candidates.json]
"""
import sys, json
from collections import defaultdict

LEVEL_RANK = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
# fixes that are the same every time; a fix written in verdicts.json always wins
DEFAULT_FIX = {"err_in_the_meantime": "'in the meantime' used for 'by the way' -> by the way"}
# impact that is the same every time for these types (30.09.26); every other error needs a label
DEFAULT_IMPACT = {"err_in_the_meantime": "m", "err_preposition": "f", "err_subject_verb_agreement": "s",
                  "err_be_plus_finite_verb": "s", "err_do_support_past": "s", "err_ed_ing_adjective": "s",
                  "a2_comparatives": "s"}
IMPACTS = {"m", "f", "s"}

RANKS = ["A1", "A2", "B1", "B2", "C1", "C2"]

def build_vocab(vc, v):
    """vc = vocab_candidates.json; v = verdicts ('vocab_drop': indices, 'offlist_drop': words,
    'offlist_levels': {word: level} = Claude's reviewed level for each kept off-list word)."""
    drop = set(int(x) for x in v.get("vocab_drop", []))
    offdrop = {w.lower() for w in v.get("offlist_drop", [])}
    offlv = {w.lower(): L for w, L in v.get("offlist_levels", {}).items() if L in RANKS}
    comeups, advanced = {}, []
    for c in vc["candidates"]:
        if c["i"] in drop: continue
        if c["type"] == "comeup":
            e = comeups.setdefault(c["id"], {"id": c["id"], "expr": c["expr"], "count": 0, "quote": c["sentence"][:300]})
            e["count"] += 1
        else:
            advanced.append({"word": c["word"], "level": c["level"], "quote": c["sentence"][:300]})
    # list-graded counts
    base = vc.get("level_counts") or {k: round(vc["tokens"] * vc["levels"].get(k, 0) / 100) for k in RANKS}
    base_m = vc.get("level_counts_by_mode", {})
    tot = {k: base.get(k, 0) for k in RANKS}
    tot_m = {m: {k: c.get(k, 0) for k in RANKS} for m, c in base_m.items()}
    # add off-list words with their estimated level
    kept, est_tokens, have = [], 0, {a["word"] for a in advanced}
    for o in vc["offlist"]:
        w = o["word"]
        if w in offdrop: continue
        L = offlv.get(w) or o.get("suggested")
        kept.append({"word": w, "level": L, "est": True, "count": o["count"]})
        if not L: continue
        tot[L] += o["count"]; est_tokens += o["count"]
        for m, n in o.get("by_mode", {}).items():
            tot_m.setdefault(m, {k: 0 for k in RANKS})[L] += n
        if RANKS.index(L) >= 3 and w not in have:
            advanced.append({"word": w, "level": L, "quote": o.get("sentence", "")[:300], "est": True})
    pct = lambda c: {k: round(c[k] / sum(c.values()) * 100, 1) if sum(c.values()) else 0 for k in RANKS}
    b2 = lambda l: round(l.get("B2", 0) + l.get("C1", 0) + l.get("C2", 0), 1)
    lv = pct(tot)
    return {
        "b2plus_by_mode": {m: (b2(pct(c)) if sum(c.values()) else None) for m, c in tot_m.items()},
        "tokens": sum(tot.values()),
        "tokens_list": vc["tokens"],
        "levels": lv,
        "b2plus_share": b2(lv),
        "b2plus_share_list": b2(vc["levels"]),
        "est": {"words": sum(1 for k in kept if k["level"]), "tokens": est_tokens,
                "basis": "frequency suggestion reviewed by Claude"},
        "advanced": advanced,
        "offlist": kept[:25],
        "comeups": sorted(comeups.values(), key=lambda e: -e["count"]),
        "mtld": vc.get("mtld"),
    }

def build_pv(pc, v, tracker_words):
    """pc = pv_candidates.json; v = verdicts ('pv_drop': indices, 'pv_relabel': {index: tracker word},
    'pv_extra': [{word, turn, mode, sentence}], 'pv_notes': {word: note})."""
    drop = set(int(x) for x in v.get("pv_drop", []))
    rel = {int(k): w for k, w in v.get("pv_relabel", {}).items()}
    uses = []
    for c in pc["candidates"]:
        if c["i"] in drop or c.get("drilled"): continue   # drilled vocab words are practice, not evidence
        uses.append({"word": rel.get(c["i"], c["word"]), "mode": c["mode"], "sentence": c["sentence"]})
    for x in v.get("pv_extra", []):
        uses.append({"word": x["word"], "mode": x.get("mode", "voice"), "sentence": x.get("sentence", "")})
    items = {}
    for u in uses:
        it = items.setdefault(u["word"], {"word": u["word"], "count": 0, "modes": [], "quote": u["sentence"][:300]})
        it["count"] += 1
        if u["mode"] not in it["modes"]: it["modes"].append(u["mode"])
    words = pc["words"]; W = sum(words.values())
    by_mode = {m: {"words": words.get(m, 0), "instances": sum(1 for u in uses if u["mode"] == m)} for m in ("voice", "typed")}
    tw = set(tracker_words)
    return {
        "words": W, "instances": len(uses), "distinct": len(items),
        "per_1000": round(len(uses) / W * 1000, 2) if W else None,
        "by_mode": by_mode,
        "items": sorted(items.values(), key=lambda i: (-i["count"], i["word"])),
        "comeups": sorted(w for w in items if w in tw),
        "new_words": sorted(w for w in items if w not in tw),
        "notes": {w: n for w, n in v.get("pv_notes", {}).items() if n},
    }

def main(cpath, vpath, date, title, doc_id, out, vocab_path=None, pv_path=None, tracker_path=None):
    data = json.load(open(cpath)); v = json.load(open(vpath))
    drop = set(int(x) for x in v.get("drop", []))
    err = {int(k): t for k, t in v.get("error", {}).items()}
    fix = {int(k): t for k, t in v.get("fix", {}).items()}
    rel = {int(k): t for k, t in v.get("relabel", {}).items()}
    imp = {int(k): t for k, t in v.get("impact", {}).items()}
    caught = set(int(x) for x in v.get("caught", []))   # corrected right away: half an error (01.10.26)

    items = []
    for c in data["candidates"]:
        i = c["i"]
        if i in drop: continue
        concept = rel.get(i, c["concept"])
        if i in err or c["kind"] == "error" or concept.startswith("err_"):
            items.append({"concept": concept, "level": c["level"] if not concept.startswith("err_") else None,
                          "result": "error", "quote": c["sentence"],
                          "fix": (err.get(i) or fix.get(i) or DEFAULT_FIX.get(concept, "")).strip(),
                          "impact": imp.get(i) or DEFAULT_IMPACT.get(concept),
                          "caught": i in caught,
                          "mode": c.get("mode", "typed"), "src": f"index {i}"})
        else:
            items.append({"concept": concept, "level": c["level"], "result": "correct", "quote": c["sentence"],
                          "mode": c.get("mode", "typed")})
    for n, x in enumerate(v.get("extra", [])):
        items.append({"concept": x["concept"], "level": x.get("level"), "result": x.get("result", "error"),
                      "quote": x["sentence"], "fix": (x.get("fix") or DEFAULT_FIX.get(x["concept"], "")).strip(),
                      "impact": x.get("impact") or DEFAULT_IMPACT.get(x["concept"]),
                      "caught": bool(x.get("caught")),
                      "mode": x.get("mode", "typed"), "src": f"extra #{n}"})

    missing = [it for it in items if it["result"] == "error" and not it["fix"]]
    if missing:
        print(f"STOP: {len(missing)} error(s) have no fix. Add each to verdicts.json "
              "(\"fix\": {index: ...} for detector lines, \"fix\" inside the item for extras) and rerun:")
        for it in missing:
            print(f'  {it["src"]} | {it["concept"]} | {it["quote"][:150]}')
        sys.exit(1)
    unlabelled = [it for it in items if it["result"] == "error" and it.get("impact") not in IMPACTS]
    if unlabelled:
        print(f"STOP: {len(unlabelled)} error(s) have no impact label (m/f/s). Add each to verdicts.json "
              "(\"impact\": {index: ...} for detector lines, \"impact\" inside the item for extras) and rerun:")
        for it in unlabelled:
            print(f'  {it["src"]} | {it["concept"]} | {it["quote"][:120]} | fix: {it.get("fix", "")[:60]}')
        sys.exit(1)

    W8 = lambda it: 0.5 if it.get("caught") else 1   # a caught error counts as half
    counts = defaultdict(lambda: {"correct": 0, "error": 0, "level": None})
    for it in items:
        c = counts[it["concept"]]; c[it["result"]] += W8(it) if it["result"] == "error" else 1; c["level"] = c["level"] or it["level"]

    errors = [dict({"concept": it["concept"], "quote": it["quote"][:300], "fix": it.get("fix", ""), "mode": it["mode"],
               "impact": it["impact"]}, **({"caught": True, "weight": 0.5} if it.get("caught") else {}))
              for it in items if it["result"] == "error"]
    etot = sum(W8(x) for x in errors)
    wbm = data.get("words_by_mode", {"voice": 0, "typed": data["words"]})
    by_mode = {}
    for m in ("voice", "typed"):
        e = sum(W8(x) for x in errors if x["mode"] == m)
        by_mode[m] = {"words": wbm.get(m, 0), "errors": e,
                      "errors_per_100": round(e / wbm[m] * 100, 2) if wbm.get(m) else None}
    # highlights: correct uses at B2+ (one quote per concept, first seen)
    seen, highlights = set(), []
    for it in items:
        if it["result"] == "correct" and LEVEL_RANK.get(it["level"] or "", 0) >= 4 and it["concept"] not in seen:
            seen.add(it["concept"]); highlights.append({"concept": it["concept"], "quote": it["quote"][:300]})

    correct_concepts = [k for k, c in counts.items() if c["correct"] > 0 and not k.startswith("err_")]
    top = max((LEVEL_RANK.get(counts[k]["level"] or "", 0) for k in correct_concepts), default=0)
    words = data["words"]
    doc = {
        "date": date, "title": title,
        "words": words,
        "observations": len(items),
        "errors_total": etot,
        "errors_per_100": round(etot / words * 100, 2) if words else None,
        "errors_caught": sum(1 for x in errors if x.get("caught")),
        "range_concepts": len(correct_concepts),
        "b2plus_correct": sum(c["correct"] for k, c in counts.items() if LEVEL_RANK.get(c["level"] or "", 0) >= 4),
        "top_level": {v: k for k, v in LEVEL_RANK.items()}.get(top),
        "concepts": {k: {"correct": c["correct"], "error": c["error"]} for k, c in sorted(counts.items())},
        "by_mode": by_mode,
        "errors": errors,
        "impact": {k: sum(1 for e in errors if e["impact"] == k) for k in ("m", "f", "s")},
        "highlights": highlights,
    }
    if vocab_path:
        doc["vocab"] = build_vocab(json.load(open(vocab_path)), v)
    if pv_path and tracker_path:
        doc["pv"] = build_pv(json.load(open(pv_path)), v, [r["word"] for r in json.load(open(tracker_path)).get("rows", [])])
    json.dump(doc, open(out, "w"), indent=1, ensure_ascii=False)
    if vocab_path:
        vv = doc["vocab"]
        print(f'vocab: B2+ share {vv["b2plus_share"]}% · {len(vv["advanced"])} B2+ words · {len(vv["comeups"])} vocab-file come-ups')
        if vv.get("mtld"):
            print(f'lexical diversity (MTLD): voice {vv["mtld"]["voice"]} · typed {vv["mtld"]["typed"]}')
    print(json.dumps({k: doc[k] for k in ("date", "words", "observations", "errors_total", "errors_per_100", "errors_caught",
                                           "range_concepts", "b2plus_correct", "top_level", "by_mode", "impact")}, indent=1))
    if doc.get("pv"):
        p = doc["pv"]
        dens = f'1 per {round(p["words"] / p["instances"])} words' if p["instances"] else "no phrasal verbs"
        print(f'phrasal verbs: {p["instances"]} uses, {p["distinct"]} different, {dens} (native 1 per 192) · '
              f'{len(p["comeups"])} tracker come-ups · new: {", ".join(p["new_words"]) or "none"}')
    print("doc_id:", doc_id)

if __name__ == "__main__":
    main(*sys.argv[1:10])
