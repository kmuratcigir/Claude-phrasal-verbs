"""Chunk-use detector for the naturalness check (added 12.10.26).

Finds candidate uses of the OPEN chunks and grammar slices in Murat's turns and suggests
correct / wrong for each. Claude verifies every line (the script finds, Claude judges).

  python3 chunks.py find  murat_turns.txt meta/chunks.json chunk_candidates.json
  python3 chunks.py apply chunk_candidates.json chunk_verdicts.json session_doc.json
  python3 chunks.py rolling sessions session_doc.json meta/chunks.json   (DOC_ID=<doc_id> in the env)

"apply" adds a `chunks` block to session_doc.json: {"open": [...], "<id>": {"voice": {uses, correct, wrong,
accuracy}, "typed": {...}, "items": [...]}}. Running it twice replaces the block (safe to rerun).

Turns file format (same as the skill's): "### T<n> [voice]" or "### T<n> [typed]", then the text.
Verdicts: {"drop": [idx..], "flip": [idx..], "caught": [idx..], "extra": [{"item": "c1", "turn": "T5",
"mode": "voice", "sentence": "...", "ok": false}]}. "flip" reverses the script's suggestion.
No third-party libraries, so it runs wherever python3 does.
"""
import json, re, sys

FILLERS = re.compile(r"\b(?:uh|um|erm|er|hmm)\b,?|\bsorry\b,?", re.I)

def clean(text):
    t = FILLERS.sub(" ", text)
    t = re.sub(r"\s+", " ", t)
    # collapse stutters: "the the the" -> "the", "a, a" -> "a"
    t = re.sub(r"\b(\w+)(?:,?\s+\1\b)+", r"\1", t, flags=re.I)
    return t.strip()

def read_turns(path):
    turns, cur = [], None
    for line in open(path, encoding="utf-8"):
        m = re.match(r"###\s*(T\d+)\s*\[(voice|typed)\]", line)
        if m:
            cur = {"turn": m.group(1), "mode": m.group(2), "text": ""}
            turns.append(cur)
        elif cur is not None:
            cur["text"] += line
    return turns

def sentences(text):
    for s in re.split(r"(?<=[.!?])\s+|\n+", text):
        s = s.strip()
        if s:
            yield s

# ---------- chunk 1: to / into after add, put, paste, devote, dedicate ----------
PREP = r"(?P<prep>into|onto|to|in|on|for|towards|toward)"
GAP = r"(?:\s+(?!(?:into|onto|to|in|on|for|towards|toward|and|but|so|because)\b)[\w'’]+){0,6}?"
VERB = {
    "add": r"add(?:s|ed|ing)?", "paste": r"past(?:e|es|ed|ing)", "devote": r"devot(?:e|es|ed|ing)",
    "dedicate": r"dedicat(?:e|es|ed|ing)", "put": r"put(?:s|ting)?",
}
C1_RX = {v: re.compile(rf"\b(?P<verb>{rx}){GAP}\s+{PREP}\b(?P<rest>(?:\s+[\w'’]+){{0,4}})", re.I) for v, rx in VERB.items()}
PHRASAL = re.compile(r"\b(?:add(?:s|ed|ing)?\s+up|put(?:s|ting)?\s+(?:off|up|on\s+(?:a|my|your|the)?\s*(?:coat|clothes|weight|music|show))|put\s+it\s+to\s+a\s+vote)\b", re.I)
PUT_OK_OBJ = re.compile(r"\b(?:list|lists|notes?|chat|document|doc|file|system|tracker|ledger|effort|time|money|work|energy|savings|hours)\b", re.I)

def c1_suggest(verb, prep, rest, span):
    v = verb.lower()
    if v.startswith("add"):
        if prep == "to": return True
        if prep in ("into", "in", "on", "onto", "towards", "toward"): return False
        return None                       # "add X for Y": not this chunk
    if v.startswith("past"):
        if prep in ("into", "in"): return True
        if prep in ("to", "on", "onto"): return False
        return None
    if v.startswith(("devot", "dedicat")):
        if prep == "to": return True
        if prep in ("for", "on", "into", "in", "towards", "toward"): return False
        return None
    # put: only with a list / notes / chat / document / system, or effort / time / money
    if not PUT_OK_OBJ.search(span): return None
    if re.search(r"\blists?\b", span, re.I):
        return prep == "on"               # put it on my list; into / in / to my list = wrong
    if prep in ("into", "in"): return True
    if prep in ("to", "on", "onto"): return False
    return None

def find_c1(sent):
    out = []
    if PHRASAL.search(sent):
        sent_scan = PHRASAL.sub(" ", sent)
    else:
        sent_scan = sent
    for v, rx in C1_RX.items():
        for m in rx.finditer(sent_scan):
            span = sent_scan[m.start():m.end()]
            ok = c1_suggest(m.group("verb"), m.group("prep").lower(), m.group("rest"), span)
            if ok is None: continue
            out.append({"item": "c1", "match": span.strip(), "suggest": ok})
    return out

# ---------- slice 1: "yet" -> present perfect ----------
YET_SKIP = re.compile(r"\byet\s+(?:another|again)\b|\b(?:best|worst|biggest|hardest)\s+yet\b|^\s*(?:and\s+|but\s+)?yet\b|[,;]\s*(?:and\s+|but\s+)?yet\s+(?:i|you|we|they|he|she|it|the|this|there)\b|^\s*not\s+yet[.!?]?\s*$", re.I)
PERFECT = re.compile(r"\b(?:have|has|haven['’]?t|hasn['’]?t|['’]ve|['’]s)\s+(?:(?:i|you|we|they|he|she|it|anyone|everyone)\s+)?(?:not\s+|never\s+|even\s+|really\s+|already\s+)?(?:been|got|gotten|done|had|\w+ed|\w+en|seen|made|said|told|found|heard|sent|left|met|come|gone|begun|taken|written|read|bought|thought|brought|caught|taught|won|lost|built|spent|run|put|set|cut|let)\b", re.I)
PAST = re.compile(r"\b(?:did|didn['’]?t|did\s+not|was|wasn['’]?t|were|weren['’]?t)\b|\b(?:couldn['’]?t)\b", re.I)

def find_s1(sent):
    if not re.search(r"\byet\b", sent, re.I): return []
    if YET_SKIP.search(sent): return []
    # look at the clause that holds "yet"
    clause = re.split(r"[,;:]|\b(?:but|and|so|because)\b", sent[:re.search(r"\byet\b", sent, re.I).end()], flags=re.I)[-1]
    if PERFECT.search(clause): ok = True
    elif PAST.search(clause): ok = False
    else: ok = None                       # Claude decides
    return [{"item": "s1", "match": clause.strip(), "suggest": ok}]

FINDERS = {"c1": find_c1, "s1": find_s1}

def cmd_find(turns_path, chunks_path, out_path):
    import os
    if not os.path.exists(chunks_path):
        json.dump({"open": [], "candidates": []}, open(out_path, "w"))
        print("No meta/chunks in the ledger: chunk counting skipped."); return
    meta = json.load(open(chunks_path, encoding="utf-8"))
    meta = meta.get("data", meta)
    open_ids = [it["id"] for it in meta["items"] if it["status"] == "open"]
    missing = [i for i in open_ids if i not in FINDERS]
    if missing:
        print("STOP: no finder yet for open item(s):", ", ".join(missing)); sys.exit(1)
    cands = []
    for t in read_turns(turns_path):
        for raw in sentences(t["text"]):
            s = clean(raw)
            for iid in open_ids:
                for c in FINDERS[iid](s):
                    c.update(turn=t["turn"], mode=t["mode"], sentence=s)
                    cands.append(c)
    for i, c in enumerate(cands): c["idx"] = i
    json.dump({"open": open_ids, "candidates": cands}, open(out_path, "w"), ensure_ascii=False, indent=1)
    print(f"CHUNK REVIEW LIST · open: {', '.join(open_ids)} · {len(cands)} candidates")
    for c in cands:
        sug = {True: "correct", False: "WRONG", None: "decide"}[c["suggest"]]
        print(f'{c["idx"]:3} {c["item"]} {c["mode"]:5} {c["turn"]:5} {sug:7} | {c["match"]} | {c["sentence"][:110]}')

def cmd_apply(cand_path, verdict_path, out_path):
    d = json.load(open(cand_path, encoding="utf-8"))
    v = json.load(open(verdict_path, encoding="utf-8")) if verdict_path != "-" else {}
    drop, flip, caught = set(v.get("drop", [])), set(v.get("flip", [])), set(v.get("caught", []))
    set_ok = {int(k): bool(x) for k, x in v.get("set", {}).items()}
    uses = []
    for c in d["candidates"]:
        i = c["idx"]
        if i in drop: continue
        ok = set_ok.get(i, c["suggest"])
        if i in flip and ok is not None: ok = not ok
        if ok is None:
            print(f"STOP: candidate {i} still needs a verdict (add it to set, flip or drop)"); sys.exit(1)
        uses.append({"item": c["item"], "mode": c["mode"], "turn": c["turn"], "ok": ok, "caught": i in caught, "sentence": c["sentence"]})
    for e in v.get("extra", []):
        uses.append({"item": e["item"], "mode": e["mode"], "turn": e["turn"], "ok": bool(e["ok"]), "caught": bool(e.get("caught")), "sentence": e["sentence"], "extra": True})
    out = {}
    for iid in d["open"]:
        blk = {}
        for mode in ("voice", "typed"):
            us = [u for u in uses if u["item"] == iid and u["mode"] == mode]
            wrong = sum(0.5 if u["caught"] else 1 for u in us if not u["ok"])
            correct = sum(1 for u in us if u["ok"]) + sum(0.5 for u in us if not u["ok"] and u["caught"])
            n = len(us)
            blk[mode] = {"uses": n, "correct": correct, "wrong": wrong, "accuracy": round(correct / n, 3) if n else None}
        blk["items"] = [u for u in uses if u["item"] == iid]
        out[iid] = blk
    out = {"open": d["open"], **out}
    if out_path.endswith("session_doc.json"):
        doc = json.load(open(out_path, encoding="utf-8"))
        doc["chunks"] = out
        json.dump(doc, open(out_path, "w"), ensure_ascii=False, indent=1)
        print(f"chunks block written into {out_path}")
    else:
        json.dump(out, open(out_path, "w"), ensure_ascii=False, indent=1)
    for iid in d["open"]:
        b = out[iid]["voice"]
        acc = "—" if b["accuracy"] is None else f'{b["accuracy"]:.0%}'
        print(f'{iid}: voice {b["uses"]} uses, {b["correct"]} correct, {b["wrong"]} wrong, accuracy {acc} · typed {out[iid]["typed"]["uses"]} uses')

def cmd_rolling(sessions_dir, sess_path, chunks_path):
    """Pool voice uses across sessions (newest last) and test the settled rule from meta/chunks."""
    import glob, os
    meta = json.load(open(chunks_path, encoding="utf-8")); meta = meta.get("data", meta)
    rule = meta["rule"]; win, tgt, min_s = rule["window_uses"], rule["target"], rule["min_sessions"]
    cur = json.load(open(sess_path, encoding="utf-8")); cur = cur.get("data", cur)
    docs = {}
    for f in glob.glob(os.path.join(sessions_dir, "*.json")):
        x = json.load(open(f, encoding="utf-8")); x = x.get("data", x)
        docs[os.path.basename(f)[:-5]] = x
    cur_id = os.environ.get("DOC_ID") or cur.get("id")
    if cur_id: docs[cur_id] = cur
    else: docs["~current"] = cur
    order = sorted(docs, key=lambda k: (k.split("_")[1] if k.count("_") >= 2 else "99999999", k))
    print("CHUNK ROLLING CHECK (voice uses, newest last)")
    for it in meta["items"]:
        if it["status"] not in ("open", "settled"): continue
        uses = []
        for k in order:
            blk = (docs[k].get("chunks") or {}).get(it["id"])
            if not blk: continue
            for u in blk.get("items", []):
                if u["mode"] == "voice": uses.append((k, u))
        last = uses[-win:]
        score = sum(1 if u["ok"] else (0.5 if u["caught"] else 0) for _, u in last)
        sess = len({k for k, _ in last})
        acc = score / len(last) if last else None
        ready = len(last) == win and sess >= min_s and acc >= tgt
        acc_s = "—" if acc is None else f"{acc:.0%}"
        print(f'{it["id"]} ({it["status"]}): last {len(last)}/{win} uses over {sess} session(s), accuracy {acc_s}'
              + (" · SUGGEST SETTLED" if ready and it["status"] == "open" else ""))

if __name__ == "__main__":
    {"find": cmd_find, "apply": cmd_apply, "rolling": cmd_rolling}[sys.argv[1]](*sys.argv[2:])
