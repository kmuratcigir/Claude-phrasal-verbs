#!/usr/bin/env python3
"""
Turkish-interference side of the naturalness check (added 27.09.26).

Two blind passes (subagents, see "Interference pass instructions" in SKILL.md) each
write {"interference": [...], "upgrades": [...]}. This script:

  merge : unions the two passes (same turn + >=50% word overlap = one item, agree=2),
          checks every pattern key against meta/interference, and prints a REVIEW LIST
          (one-pass items and unknown pattern keys) for Claude to verify.
  apply : applies Claude's intf_verdicts.json, adds the "interference" block to
          session_doc.json, and writes meta_interference_out.json if new patterns were added.

Usage:
  python3 intf.py merge intf_A.json intf_B.json meta/interference.json intf_merged.json
  python3 intf.py apply intf_merged.json intf_verdicts.json meta/interference.json session_doc.json meta_interference_out.json

intf_verdicts.json:
  {"drop": [3, 17],                        # indices of merged items that are not interference
   "pattern": {"5": "by_the_way"},         # re-assign an item's pattern key
   "upgrade_drop": [2],                    # upgrade suggestions that are not useful
   "new_patterns": [{"key": "...", "label": "...", "turkish": "...", "type": "...", "fix": "..."}],
   "impact": {"9": "m"}}                   # optional: override an item's impact (m / f / s)
Impact (30.09.26): every item gets m = changes the meaning, f = sounds foreign, s = slip.
The default comes from the pattern, then its type (see PATTERN_IMPACT / TYPE_IMPACT); set it in
"impact" only when this item is different (e.g. a false friend that didn't change the meaning).
Voice "missing_article" items count only when that pattern occurs 2+ times in voice in the
session (the transcriber can drop small words); single ones are kept but not counted.
"""
import json, re, sys

tok = lambda s: set(re.findall(r"[a-z']+", s.lower()))
T = lambda t: str(t).lstrip("T")
RANK = {"high": 3, "medium": 2, "low": 1}
PATTERN_IMPACT = {"by_the_way": "m", "thats_why": "m"}
TYPE_IMPACT = {"article": "s", "pro_drop": "s", "lex_false_friend": "m"}   # every other type: "f"

def same(a, b):
    if T(a["turn"]) != T(b["turn"]): return False
    ta, tb = tok(a["quote"]), tok(b["quote"])
    return len(ta & tb) / max(1, min(len(ta), len(tb))) >= 0.5

def union(ia, ib, interf):
    used, out = set(), []
    for a in ia:
        m = next((j for j, b in enumerate(ib) if j not in used and same(a, b)), None)
        if m is None:
            out.append(dict(a, agree=1)); continue
        used.add(m); b = ib[m]
        best = a if RANK.get(a.get("confidence"), 0) >= RANK.get(b.get("confidence"), 0) else b
        x = dict(best, agree=2)
        if a.get("caught") or b.get("caught"): x["caught"] = True   # either pass saw a self-correction
        if interf and a.get("pattern") != b.get("pattern"):
            x["pattern_alt"] = b.get("pattern") if x is a else a.get("pattern")
        out.append(x)
    out += [dict(b, agree=1) for j, b in enumerate(ib) if j not in used]
    for x in out: x["turn"] = "T" + T(x["turn"])
    out.sort(key=lambda x: int(T(x["turn"])))
    return out

def load_pass(path):
    """A pass file must exist, be valid JSON and hold an "interference" list (added 30.09.26)."""
    try:
        d = json.load(open(path))
    except FileNotFoundError:
        sys.exit(f"STOP: {path} is missing. That pass didn't finish: run it again, then merge.")
    except json.JSONDecodeError:
        sys.exit(f"STOP: {path} is not valid JSON (the pass may have stopped mid-write): run it again, then merge.")
    if not isinstance(d.get("interference"), list):
        sys.exit(f'STOP: {path} has no "interference" list: run that pass again, then merge.')
    return d

def merge(pa, pb, metap, out):
    A, B, meta = load_pass(pa), load_pass(pb), json.load(open(metap))
    for (x, px), (y, py) in (((A, pa), (B, pb)), ((B, pb), (A, pa))):
        if not x["interference"] and len(y["interference"]) >= 5:
            sys.exit(f"STOP: {px} found nothing while {py} found {len(y['interference'])}. "
                     "The empty pass probably failed: run it again, then merge.")
    keys = {p["key"] for p in meta["patterns"]}
    items = union(A["interference"], B["interference"], True)
    ups = union(A.get("upgrades", []), B.get("upgrades", []), False)
    for i, x in enumerate(items): x["i"] = i
    for i, x in enumerate(ups): x["i"] = i
    json.dump({"interference": items, "upgrades": ups}, open(out, "w"), indent=1, ensure_ascii=False)
    both = sum(x["agree"] == 2 for x in items)
    print(f"interference: A {len(A['interference'])} · B {len(B['interference'])} · union {len(items)} · both passes {both}")
    print(f"upgrades: {len(ups)}")
    print("REVIEW LIST  (index | agree | pattern | type | quote -> fix)   [only one-pass items, unknown keys and key disagreements]")
    for x in items:
        unk = x.get("pattern") not in keys
        if x["agree"] == 1 or unk or x.get("pattern_alt"):
            flag = ("UNKNOWN KEY " if unk else "") + (f"alt={x['pattern_alt']} " if x.get("pattern_alt") else "")
            print(f'{x["i"]:4} | {x["agree"]} | {x.get("pattern")} {flag}| {x["type"]} | {x["turn"]} {x["mode"][0]}: {x["quote"][:90]} -> {x.get("fix","")[:50]}')
    sc = [x for x in items if x.get("caught") or re.search(r"\bsorry\b|\bI mean\b|\bnot (?:in the meantime|that)\b", x["quote"], re.I)]
    print("SELF-CORRECTION CHECK  (index | quote)   [did he correct it right away? -> \"caught\"; check all]")
    for x in sc:
        print(f'{x["i"]:4} | {x["turn"]} {x["mode"][0]}: {x["quote"][:120]}')
    print("UPGRADES  (index | quote -> suggestion)")
    for u in ups:
        print(f'{u["i"]:4} | {u["turn"]} {u["mode"][0]}: {u["quote"][:80]} -> {u.get("suggestion","")[:60]}')

def apply(mp, vp, metap, sp, metaout):
    M, v, meta, doc = json.load(open(mp)), json.load(open(vp)), json.load(open(metap)), json.load(open(sp))
    drop = set(int(i) for i in v.get("drop", []))
    re_p = {int(k): p for k, p in v.get("pattern", {}).items()}
    udrop = set(int(i) for i in v.get("upgrade_drop", []))
    imp = {int(k): x for k, x in v.get("impact", {}).items() if x in ("m", "f", "s")}
    rpt = set(int(i) for i in v.get("repeat", []))     # game repeats: counted once per session (01.10.26)
    cgt = set(int(i) for i in v.get("caught", []))     # corrected right away: half (01.10.26)
    known = {p["key"] for p in meta["patterns"]}
    added = [p for p in v.get("new_patterns", []) if p["key"] not in known]
    meta["patterns"] += added; known |= {p["key"] for p in added}
    pmap = {p["key"]: p for p in meta["patterns"]}
    W = {m: doc["by_mode"][m]["words"] for m in ("voice", "typed")}
    items = []
    for x in M["interference"]:
        if x["i"] in drop: continue
        k = re_p.get(x["i"], x.get("pattern"))
        if k not in known:
            sys.exit(f'item {x["i"]} has unknown pattern "{k}": map it in "pattern" or add it to "new_patterns"')
        items.append({"turn": x["turn"], "mode": x["mode"], "quote": x["quote"][:300], "pattern": k, "type": pmap[k]["type"],
                      "turkish": x.get("turkish_source", "")[:120], "fix": x.get("fix", "")[:200],
                      "confidence": x.get("confidence"), "agree": x["agree"],
                      "impact": imp.get(x["i"]) or PATTERN_IMPACT.get(k) or TYPE_IMPACT.get(pmap[k]["type"], "f"),
                      "_i": x["i"]})
    va = [x for x in items if x["pattern"] == "missing_article" and x["mode"] == "voice"]
    for x in items:
        x["counted"] = not (x in va and len(va) < 2)
        if x["_i"] in rpt: x["counted"] = False; x["excluded"] = "repeat of the same game reply; counted once per session"
        if x["_i"] in cgt: x["caught"] = True; x["weight"] = 0.5
        del x["_i"]
    W8 = lambda x: 0.5 if x.get("caught") else 1
    bm = {}
    for m in ("voice", "typed"):
        c = sum(W8(x) for x in items if x["mode"] == m and x["counted"])
        bm[m] = {"words": W[m], "count": c, "per_100": round(c / W[m] * 100, 2) if W[m] else None}
    tot, words = bm["voice"]["count"] + bm["typed"]["count"], W["voice"] + W["typed"]
    ups = [{"turn": u["turn"], "mode": u["mode"], "quote": u["quote"][:300], "suggestion": u.get("suggestion", "")[:200],
            "why": u.get("why", "")[:200]} for u in M["upgrades"] if u["i"] not in udrop]
    doc["interference"] = {"method": "two blind passes, union, verified by Claude", "count": tot,
                           "per_100": round(tot / words * 100, 2) if words else None, "by_mode": bm, "items": items,
                           "upgrades": ups, "patterns_seen": sorted({x["pattern"] for x in items if x["counted"]}),
                           "impact": {k: sum(1 for x in items if x["counted"] and x["impact"] == k) for k in ("m", "f", "s")},
                           "caught": sum(1 for x in items if x["counted"] and x.get("caught"))}
    json.dump(doc, open(sp, "w"), indent=1, ensure_ascii=False)
    if added:
        json.dump(meta, open(metaout, "w"), ensure_ascii=False)
    top = {}
    for x in items:
        if x["counted"]: top[x["pattern"]] = top.get(x["pattern"], 0) + W8(x)
    print(json.dumps({"by_mode": bm, "upgrades": len(ups), "caught": doc["interference"]["caught"],
                      "repeats_not_counted": sum(1 for x in items if x.get("excluded")), "new_patterns": [p["key"] for p in added],
                      "impact": doc["interference"]["impact"],
                      "top": sorted(top.items(), key=lambda z: -z[1])[:8]}, indent=1, ensure_ascii=False))
    if added: print(f"meta/interference changed: write {metaout} back with if_version")

if __name__ == "__main__":
    {"merge": merge, "apply": apply}[sys.argv[1]](*sys.argv[2:])
