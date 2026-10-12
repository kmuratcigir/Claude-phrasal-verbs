#!/usr/bin/env python3
"""
Link new phrasal verbs to the native core (meta/phave) so the Native core panel stays honest.

For each word in the session's pv.new_words: if it starts with one of the 150 core phrasal
verbs (first word compared by its base form, so "went on with" -> "go on"), add it to that core
item's `rows`. The longest matching core verb wins. Different verbs that only look like
variants never link: "get up to", "get in touch with", "hold on to".

Writes phave_out.json only when something changed (it then goes into Step 7's single save).

Usage: python3 phave_link.py meta/phave.json session_doc.json phave_out.json
"""
import json, os, sys
import spacy

nlp = spacy.load("en_core_web_sm")
NEVER = {"get up to", "get in touch with", "hold on to"}
IRREG = {"got": "get", "took": "take", "came": "come", "went": "go", "gave": "give", "held": "hold",
         "kept": "keep", "brought": "bring", "ran": "run", "put": "put", "set": "set", "made": "make",
         "found": "find", "left": "leave", "thought": "think", "told": "tell", "stood": "stand"}

def base(first):
    w = first.lower()
    return IRREG.get(w) or nlp(w)[0].lemma_.lower()

def main(phave_path, sess_path, out):
    ph = json.load(open(phave_path)); ph = ph.get("data", ph)
    s = json.load(open(sess_path)); s = s.get("data", s)
    new = (s.get("pv") or {}).get("new_words", [])
    items = ph["items"]
    changes = []
    for w in new:
        toks = w.lower().replace("(", " ").replace(")", " ").split()
        if not toks or w.lower() in NEVER or any(w.lower().startswith(n) for n in NEVER): continue
        toks = [base(toks[0])] + toks[1:]
        best = None
        for it in items:
            core = it["word"].lower().split()
            if toks[:len(core)] == core and (best is None or len(core) > len(best["word"].split())):
                best = it
        if best and w not in best.setdefault("rows", []):
            best["rows"].append(w); changes.append(f'{w} -> core #{best["rank"]} {best["word"]}')
    if changes:
        json.dump(ph, open(out, "w"), ensure_ascii=False)
        print("linked:", "; ".join(changes), f"\nwrite {out} in Step 7")
    else:
        if os.path.exists(out): os.remove(out)
        print("no new core variants; meta/phave unchanged")

if __name__ == "__main__":
    main(*sys.argv[1:4])
