"""English Mastery scores from the raw counts (added 02.11.26). The Ledger page computes the same
numbers in JavaScript; this is the same arithmetic for the skills (and the tests).

  python3 scores.py <sessions_dir> <scoring.json> <registry.json> [--mode voice|typed|all] [--json out.json]
                    [--today session_doc.json --id <doc_id>]

--today adds this chat's session before it is saved (replacing the saved copy of the same doc id).

Prints, for the latest session and cumulatively, Grammar / Vocabulary / Speaking with their parts.
Rules (meta/scoring): cumulative = totals first, then divided; voice and typed scored separately;
"all" = word-weighted; speaking = voice only.
"""
import glob, json, os, sys

LV = ("A1", "A2", "B1", "B2", "C1", "C2")

def load(p):
    d = json.load(open(p, encoding="utf-8")); return d.get("data", d) if isinstance(d, dict) and "data" in d and len(d) <= 3 else d
def clip(v): return max(0.0, min(100.0, v))
def lin(v, a, b): return clip((v - a) / (b - a) * 100)
def dkey(d): dd, mm, yy = d["date"].split("."); return yy + mm + dd

def concepts(registry):
    return {k: v[1] for k, v in registry["concepts"].items() if not k.startswith(("err_", "old_")) and v[1]}

def sessions(sdir):
    out = []
    for p in sorted(glob.glob(os.path.join(sdir, "*.json"))):
        d = load(p)
        if d.get("mastery"): d["_id"] = os.path.basename(p)[:-5]; out.append(d)
    return sorted(out, key=lambda d: (dkey(d), d["_id"]))

# ---------------------------------------------------------------- grammar
def grammar(ss, i, mode, sc, conc, cumulative=False):
    g = sc["grammar"]; W = g["level_weights"]
    blk = lambda s: (s["mastery"].get("grammar") or {}).get(mode) or {}
    cur = blk(ss[i])
    if not cumulative and not any(v["c"] + v["e"] for v in (cur.get("concepts") or {}).values()): return None
    rng = ss[: i + 1] if cumulative else ss[max(0, i - g["range_sessions"] + 1): i + 1]
    # mastery: last window_uses uses, reaching back by whole sessions (cumulative: all uses)
    num = den = 0.0; per = []
    for k, lvl in conc.items():
        c = u = 0.0
        for s in reversed(ss[: i + 1]):
            x = (blk(s).get("concepts") or {}).get(k)
            if x: c += x["c"]; u += x["c"] + x["e"]
            if not cumulative and u >= g["window_uses"]: break
        if u >= g["min_uses"]:
            num += W[lvl] * c / u; den += W[lvl]; per.append({"id": k, "lvl": lvl, "c": round(c, 1), "n": round(u, 1), "pct": round(100 * c / u)})
    mastery = 100 * num / den if den else None
    sents = [blk(s) for s in (ss[: i + 1] if cumulative else [ss[i]]) if blk(s).get("sentences")]
    clean = 100 * (1 - sum(b["grammar_err_sentences"] for b in sents) / sum(b["sentences"] for b in sents)) if sents else None
    acc = None if mastery is None else (mastery if clean is None else (mastery + clean) / 2)
    used = {k for s in rng for k, x in (blk(s).get("concepts") or {}).items() if k in conc and x["c"] > 0}
    possible = sum(W[l] for l in conc.values()); earned = sum(W[conc[k]] for k in used)
    range_ = 100 * earned / possible
    levels = {l: sum(1 for k in used if conc[k] == l) for l in LV}
    score = None if acc is None else (acc + range_) / 2
    return {"score": score, "accuracy": acc, "mastery": mastery, "clean": clean, "range": range_, "used": len(used),
            "of": len(conc), "earned": earned, "possible": possible, "levels": levels, "concepts": sorted(per, key=lambda x: x["pct"])}

# ---------------------------------------------------------------- vocabulary
def vocab(ss, i, mode, sc, cumulative=False):
    v = sc["vocab"]; W = v["level_weights"]
    blk = lambda s: (s["mastery"].get("vocab") or {}).get(mode) or {}
    part = ss[: i + 1] if cumulative else [ss[i]]
    ok = [blk(s) for s in part if blk(s).get("unique") and blk(s).get("words")]
    if not ok: return None
    wp = sum(b["b2"] * W["B2"] + b["c1"] * W["C1"] + b["c2"] * W["C2"] for b in ok)
    share = 100 * wp / sum(b["unique"] for b in ok)
    range_ = clip(share / v["range_full_share"] * 100)
    if cumulative:
        seen = {}
        for s in ss[: i + 1]:
            for w in blk(s).get("adv_words") or []: seen[w] = seen.get(w, 0) + 1
        reuse = 100 * sum(1 for n in seen.values() if n >= 2) / len(seen) if seen else 0.0
        reused, adv_n = sum(1 for n in seen.values() if n >= 2), len(seen)
    else:
        before = {w for s in ss[:i] for w in (blk(s).get("adv_words") or [])}
        today = blk(ss[i]).get("adv_words") or []
        reused, adv_n = sum(1 for w in today if w in before), len(today)
        reuse = 100 * reused / adv_n if adv_n else 0.0
    pts = sum(b["lex_problems"] + (v["m_points"] - 1) * b["lex_m"] for b in ok)
    words = sum(b["words"] for b in ok)
    rate = 100 * pts / words
    acc = clip(100 - rate / v["acc_zero_rate"] * 100)
    return {"score": (range_ + reuse + acc) / 3, "range": range_, "share": share, "reuse": reuse, "reused": reused,
            "adv": adv_n, "accuracy": acc, "rate": rate, "points": pts, "problems": sum(b["lex_problems"] for b in ok),
            "m": sum(b["lex_m"] for b in ok), "words": words, "unique": sum(b["unique"] for b in ok),
            "b2": sum(b["b2"] for b in ok), "c1": sum(b["c1"] for b in ok), "c2": sum(b["c2"] for b in ok)}

# ---------------------------------------------------------------- speaking (voice only)
def speaking(ss, i, sc, cumulative=False):
    P = sc["speaking"]
    part = [s["mastery"].get("speaking") for s in (ss[: i + 1] if cumulative else [ss[i]])]
    part = [p for p in part if p and p.get("replies")]
    if not part: return None
    T = {k: sum(p.get(k, 0) for p in part) for k in ("replies", "words", "clean_words", "reply_clean_words", "developed", "connectors", "hesitations", "word_fillers")}
    m = {"flow": (T["reply_clean_words"] or T["clean_words"]) / T["replies"], "depth": 100 * T["developed"] / T["replies"],
         "cohesion": 100 * T["connectors"] / T["clean_words"], "fillers": 100 * (T["hesitations"] + T["word_fillers"]) / T["words"]}
    if not P.get("calibrated"): return {"score": None, "measures": m, "calibrating": True}
    p = {k: lin(m[k], P[k]["zero"], P[k]["full"]) for k in m}
    return {"score": sum(p.values()) / 4, "measures": m, "points": p}

def combine(a, b, wa, wb):
    if a is None or a.get("score") is None: return b
    if b is None or b.get("score") is None or not wb: return a
    return {"score": (a["score"] * wa + b["score"] * wb) / (wa + wb)}

def area(ss, i, mode, sc, conc, name, cumulative=False):
    f = {"grammar": lambda m: grammar(ss, i, m, sc, conc, cumulative), "vocab": lambda m: vocab(ss, i, m, sc, cumulative)}[name]
    if mode != "all": return f(mode)
    words = lambda m: sum((s.get("by_mode") or {}).get(m, {}).get("words", 0) for s in (ss[: i + 1] if cumulative else [ss[i]]))
    return combine(f("voice"), f("typed"), words("voice"), words("typed"))

def main(sdir, scp, regp, mode="voice", out=None, today=None, today_id=None):
    ss = sessions(sdir); sc = load(scp); conc = concepts(load(regp))
    if today:
        d = load(today); d["_id"] = today_id or "zz_today"
        ss = sorted([s for s in ss if s["_id"] != d["_id"]] + ([d] if d.get("mastery") else []), key=lambda d: (dkey(d), d["_id"]))
    res = []
    for i, s in enumerate(ss):
        res.append({"id": s["_id"], "date": s["date"],
                    "grammar": area(ss, i, mode, sc, conc, "grammar"), "vocab": area(ss, i, mode, sc, conc, "vocab"),
                    "speaking": speaking(ss, i, sc) if mode != "typed" else None})
    i = len(ss) - 1
    cum = {"grammar": area(ss, i, mode, sc, conc, "grammar", True), "vocab": area(ss, i, mode, sc, conc, "vocab", True),
           "speaking": speaking(ss, i, sc, True) if mode != "typed" else None}
    r = lambda x: "–" if not x or x.get("score") is None else str(round(x["score"]))
    prev = res[-2] if len(res) > 1 else None
    def ch(k):
        a, b = res[-1][k], prev and prev[k]
        if not a or a.get("score") is None or not b or b.get("score") is None: return ""
        d = round(a["score"]) - round(b["score"]); return f" ({'+' if d >= 0 else ''}{d} vs {prev['date'][:5]})"
    k = sum(1 for x in ss if (x["mastery"].get("speaking") or {}).get("replies"))
    calib = f"calibrating ({k} of {(sc['speaking'].get('calibration') or {}).get('sessions_needed', 5)} sessions)"
    print(f"MASTERY ({mode}) {res[-1]['date']}: Grammar {r(res[-1]['grammar'])}{ch('grammar')}, Vocabulary {r(res[-1]['vocab'])}{ch('vocab')}, "
          f"Speaking {r(res[-1]['speaking']) if res[-1]['speaking'] and not res[-1]['speaking'].get('calibrating') else (calib if not sc['speaking'].get('calibrated') else '–')}"
          f"{ch('speaking')} · cumulative {len(ss)} sessions: Grammar {r(cum['grammar'])}, Vocabulary {r(cum['vocab'])}, "
          f"Speaking {r(cum['speaking']) if cum['speaking'] and not cum['speaking'].get('calibrating') else (calib if not sc['speaking'].get('calibrated') else '–')}")
    if out: json.dump({"daily": res, "cumulative": cum}, open(out, "w"), indent=1, default=float)
    return res, cum

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 3: sys.exit(__doc__)
    mode = a[a.index("--mode") + 1] if "--mode" in a else "voice"
    out = a[a.index("--json") + 1] if "--json" in a else None
    today = a[a.index("--today") + 1] if "--today" in a else None
    tid = a[a.index("--id") + 1] if "--id" in a else None
    main(a[0], a[1], a[2], mode, out, today, tid)
