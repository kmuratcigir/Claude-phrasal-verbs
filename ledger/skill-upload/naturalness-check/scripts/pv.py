#!/usr/bin/env python3
"""
Phrasal verb side of the naturalness check (added 26.09.26; replaces the old
phrasal-verb-tracker skill's "read the chat and spot them" step, the same
eyeballing method that failed for grammar).

Finds every phrasal verb CANDIDATE in Murat's turns, three ways:
  A. spaCy particles: any verb with a `prt` child ("turn it off", "pick her up",
     "figure out") -> verb + particle, split forms included.
  B. Tracker matching: every expression on the tracker ("deal with",
     "take care of", "get back to (someone)") matched on lemmas with small gaps,
     so prepositional verbs that spaCy doesn't mark as particles are caught.
  C. Adverbial particles spaCy reads as prepositions right after a verb
     ("went through", "came across"), for words not yet on the tracker.
Claude then verifies every line (drop / relabel / extra) before anything counts.

Usage: python3 pv.py murat_turns.txt meta/pv_tracker.json pv_candidates.json [drilled_words.txt]
"""
import json, os, re, sys
import spacy
from detect import clean, load_turns
from vocab import expand_alts, match

nlp = spacy.load("en_core_web_sm")
PARTICLES_C = {"up", "down", "out", "off", "away", "back", "over", "around", "round", "through",
               "across", "along", "apart", "aside", "forward", "about", "into", "onto"}
SKIP_VERBS = {"be", "have", "do"}
WILD = {"something", "someone", "somebody", "someone's", "yourself", "it", "the", "a", "same",
        "page", "steam", "nowhere", "left"}

def canon(verb, prt):
    return f"{verb} {prt}".lower()

def compile_tracker(rows):
    """-> [{word, seq}] with seq = list of (lemma, gap) for vocab.match()."""
    pats = []
    for r in rows:
        for alt in expand_alts(r["word"]):
            s = re.sub(r"\([^)]*\)", " ", alt.lower()).replace("-", " ")
            toks = [t for t in nlp(" ".join(s.split()))]
            seq, gap = [], 0
            for t in toks:
                if t.text in WILD: gap = 3; continue
                if not t.is_alpha: continue
                seq.append((t.lemma_.lower(), gap if seq else 0)); gap = 2
            if len(seq) >= 2:
                pats.append({"word": r["word"], "seq": seq})
    return pats

def main(turns_path, tracker_path, out, drilled_path=None):
    rows = json.load(open(tracker_path)).get("rows", [])
    pats = compile_tracker(rows)
    # (verb, particle) -> tracker word, for mapping A/C hits onto tracker entries
    two = {}
    for p in pats:
        if len(p["seq"]) == 2: two.setdefault((p["seq"][0][0], p["seq"][1][0]), p["word"])
    drilled = set()
    if drilled_path and os.path.exists(drilled_path):
        drilled = {l.strip().lower() for l in open(drilled_path, encoding="utf-8") if l.strip()}
    words = {"voice": 0, "typed": 0}
    cands = []
    for turn, raw, mode in load_turns(turns_path):
        text = clean(raw)
        words[mode] += len(re.findall(r"[A-Za-z']+", text))
        for s in nlp(text).sents:
            lemmas = [t.lemma_.lower() for t in s]
            found = {}   # word -> {source, split, on_tracker, seq}
            for p in pats:
                if match(p["seq"], lemmas):
                    found.setdefault(p["word"], {"source": "tracker", "split": False, "on_tracker": True,
                                                 "seq": [l for l, _ in p["seq"]]})
            for v in s:
                if v.pos_ not in ("VERB", "AUX") or v.lemma_.lower() in SKIP_VERBS: continue
                for c in v.children:
                    src = None
                    if c.dep_ == "prt": src = "particle"
                    elif c.dep_ == "prep" and c.lower_ in PARTICLES_C and c.i == v.i + 1: src = "prep"
                    if not src: continue
                    key = (v.lemma_.lower(), c.lower_)
                    word = two.get(key, canon(*key))
                    f = found.setdefault(word, {"source": src, "split": False, "on_tracker": word in two.values(),
                                                "seq": list(key)})
                    f["split"] = f["split"] or c.i > v.i + 1
            # drop a match whose lemmas are the start of a longer match in the same sentence
            # ("got back" inside "get back to (someone)", "get back" inside it too)
            keep = {w: f for w, f in found.items()
                    if not any(o is not f and len(o["seq"]) > len(f["seq"]) and o["seq"][:len(f["seq"])] == f["seq"]
                               for o in found.values())}
            for word, f in keep.items():
                cands.append({"i": len(cands), "turn": turn, "mode": mode, "word": word, "source": f["source"],
                              "split": f["split"], "on_tracker": f["on_tracker"],
                              "drilled": word.lower() in drilled, "sentence": s.text.strip()})
    json.dump({"words": words, "candidates": cands}, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"{sum(words.values())} words (voice {words['voice']}, typed {words['typed']}) · {len(cands)} phrasal verb candidates")
    print("PHRASAL VERB REVIEW LIST  (index | word | source | flags | sentence)")
    for c in cands:
        flags = ",".join(f for f, on in (("tracker", c["on_tracker"]), ("NEW", not c["on_tracker"]),
                                         ("split", c["split"]), ("drilled", c["drilled"])) if on)
        print(f'{c["i"]:4} | {c["word"]} | {c["source"]} | {flags} | {c["turn"]} {c["mode"][0]}: {c["sentence"][:150]}')

if __name__ == "__main__":
    main(*sys.argv[1:5])
