#!/usr/bin/env python3
"""
Vocabulary side of the naturalness check.

1. CEFR profile: every word Murat used is looked up in the CEFR-J list (A1-B2)
   and the Octanove list (C1-C2) -> level distribution + the B2+ words he used.
2. Vocab-file come-ups: every expression on his vocabulary list is matched
   against his sentences (lemmas, gaps allowed for objects/separable particles),
   so a practised word that turns up unprompted is logged with its quote.
3. Lexical diversity (MTLD): how varied his words are, voice and typed separately.

Like detect.py, this only FINDS candidates. Claude reviews the REVIEW LIST and
drops false hits (quoting a text, talking about a word, words drilled in that
chat's vocab session) before anything is logged.

Usage: python3 vocab.py murat_turns.txt vocab_items.json <cefr_dir> vocab_candidates.json [drilled_words.txt]
  vocab_items.json: meta/vocab_tracker ({"rows": [{"id": 49, "expr": "Dwell (on something)", ...}]});
  the old {"items": [...]} shape is also accepted
  cefr_dir: clone of github.com/openlanguageprofiles/olp-en-cefrj
"""
import csv, json, os, re, sys
from collections import Counter
import spacy
from detect import clean, load_turns, turn_tags
try:
    from wordfreq import zipf_frequency
except ImportError:
    zipf_frequency = None

def suggest_level(z):
    """Rough frequency -> CEFR guess for words missing from both lists. Claude reviews every one."""
    if z is None: return None
    return "A1" if z >= 5 else "A2" if z >= 4.5 else "B1" if z >= 4 else "B2" if z >= 3.5 else "C1" if z >= 3 else "C2"

nlp = spacy.load("en_core_web_sm")
RANK = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

def mtld(tokens, ttr=0.72, min_len=10):
    """MTLD (McCarthy & Jarvis 2010), TAALED variant: a factor closes when the running
    type-token ratio drops below 0.72 with at least 10 words; the leftover counts as a
    partial factor; forwards and backwards are averaged. Higher = more varied words.
    Matches the lexical_diversity package's mtld() exactly (checked 26.09.26)."""
    def one_way(ts):
        factors, types, count = 0.0, set(), 0
        for t in ts:
            count += 1; types.add(t)
            if len(types) / count < ttr and count >= min_len:
                factors += 1; types, count = set(), 0
        if count:
            factors += (1 - len(types) / count) / (1 - ttr)
        return len(ts) / factors if factors else 0.0
    return (one_way(tokens) + one_way(tokens[::-1])) / 2

MTLD_MIN = 100   # below this many words MTLD isn't meaningful; stored as null

def load_levels(d):
    lvl = {}
    for f in ("cefrj-vocabulary-profile-1.5.csv", "octanove-vocabulary-profile-c1c2-1.0.csv"):
        for r in csv.DictReader(open(os.path.join(d, f), encoding="utf-8")):
            for h in r["headword"].split("/"):
                h = h.strip().lower()
                if h and (h not in lvl or RANK[r["CEFR"]] < RANK[lvl[h]]):
                    lvl[h] = r["CEFR"]
    return lvl

def level_of(tok, lvl):
    """Lemma first, then surface form, then fold common derivations back to a base."""
    w, l = tok.text.lower(), tok.lemma_.lower()
    for c in (l, w):
        if c in lvl: return lvl[c], c
    cands = []
    if w.endswith("ily"): cands.append(w[:-3] + "y")
    if w.endswith("ly"): cands += [w[:-2], w[:-2] + "e"]
    if w.endswith("ing"): cands += [w[:-3], w[:-3] + "e"]
    if w.endswith("ed"): cands += [w[:-2], w[:-1], w[:-2] + "e"]
    if w.endswith("ness"): cands.append(w[:-4])
    for c in cands:
        if c in lvl: return lvl[c], c
    return None, l

WILD = {"something", "someone", "somebody", "someone's", "somewhere", "your", "yourself",
        "you", "x", "y", "their", "his", "her", "my", "you've", "do", "doing"}
# A pattern that shrinks to one of these single words would fire on almost any
# sentence ("make it" -> "make", "be through" -> "through"), so it is skipped.
TOO_COMMON = {"make", "get", "go", "come", "keep", "take", "have", "put", "do", "give", "look",
              "run", "set", "turn", "bring", "through", "up", "down", "out", "off", "in", "on"}

PREP = {"to", "with", "for", "at", "by", "of", "into", "about", "from"}

def expand_alts(expr):
    """'Go/come full circle' -> ['go full circle', 'come full circle'];
    'Slope up/down' -> ['slope up', 'slope down']; 'A / B' -> ['A', 'B']."""
    out = []
    for part in re.split(r"\s+/\s+", expr):
        m = re.search(r"(\S+)/(\S+)", part)
        if m:
            out += [part[:m.start()] + m.group(1) + part[m.end():], part[:m.start()] + m.group(2) + part[m.end():]]
        else:
            out.append(part)
    return out
LEAD = {"to", "be", "being", "a", "an", "the"}

def compile_items(items):
    pats = []
    for it in items:
        for alt in expand_alts(it["expr"]):
            s = re.sub(r"\([^)]*\)", " ", alt.lower())
            s = re.sub(r"\+\s*-ing", " ", s).replace("-", " ")
            toks = s.split()
            while toks and toks[0] in LEAD and len(toks) > 1: toks = toks[1:]
            if not toks: continue
            seq = []  # list of (lemma, gap_allowed_before)
            gap = 0
            doc = nlp(" ".join(toks))
            for t in doc:
                if t.text in WILD or t.text == "'s":
                    gap = 3; continue
                if not t.is_alpha and t.text != "'t": continue
                seq.append((t.lemma_.lower(), gap if seq else 0))
                gap = 2
            if not seq or (len(seq) == 1 and seq[0][0] in TOO_COMMON): continue
            if len(seq) == 2 and seq[0][0] in TOO_COMMON and seq[1][0] in PREP: continue   # "get to", "come to"
            pats.append({"id": it["id"], "expr": it["expr"], "seq": seq})
    return pats

def match(seq, lemmas):
    """Ordered lemma match; each token may sit up to `gap` tokens after the previous."""
    n = len(lemmas)
    for start in range(n):
        if lemmas[start] != seq[0][0]: continue
        pos, ok = start, True
        for lem, gap in seq[1:]:
            nxt = next((j for j in range(pos + 1, min(n, pos + 2 + gap)) if lemmas[j] == lem), None)
            if nxt is None: ok = False; break
            pos = nxt
        if ok: return True
    return False

def mtld_block(div):
    allw = div["voice"] + div["typed"]
    val = lambda ws: round(mtld(ws), 1) if len(ws) >= MTLD_MIN else None
    return {"all": val(allw), "voice": val(div["voice"]), "typed": val(div["typed"]),
            "words": {m: len(ws) for m, ws in div.items()}}

def main(turns_path, items_path, cefr_dir, out, drilled_path=None):
    """drilled_path: optional file, one expression per line, of words drilled in this
    chat's vocab session. Their hits INSIDE the vocab drill marks (turns tagged [vocab-drill])
    are practice, not come-ups; outside the marks they are real come-ups (29.10.26)."""
    lvl = load_levels(cefr_dir)
    drilled = set()
    if drilled_path and os.path.exists(drilled_path):
        drilled = {l.strip().lower() for l in open(drilled_path, encoding="utf-8") if l.strip()}
    src = json.load(open(items_path)); src = src.get("data", src)
    items = [{"id": it["id"], "expr": it["expr"]} for it in (src.get("items") or src["rows"])]
    in_drill = {t for t, tg in turn_tags(turns_path).items() if "vocab-drill" in tg}
    kept_out = 0
    pats = compile_items(items)
    levels, tokens = Counter(), 0
    mlevels = {"voice": Counter(), "typed": Counter()}
    adv, off, hits = {}, Counter(), []
    off_mode, off_sent = {}, {}
    seen_hit = set()
    div = {"voice": [], "typed": []}   # word tokens for MTLD, same word rule as detect.py
    uniq = set()
    for turn, raw, mode in load_turns(turns_path):
        div[mode] += [w.lower() for w in re.findall(r"[A-Za-z']+", clean(raw))]
        doc = nlp(clean(raw))
        for s in doc.sents:
            lemmas = [t.lemma_.lower() for t in s]
            for p in pats:
                key = (p["id"], turn)
                if key in seen_hit: continue
                if match(p["seq"], lemmas):
                    seen_hit.add(key)
                    if p["expr"].strip().lower() in drilled and turn in in_drill:
                        kept_out += 1; continue   # practice inside the drill marks
                    hits.append({"id": p["id"], "expr": p["expr"], "turn": turn, "mode": mode, "sentence": s.text.strip()})
            for t in s:
                if not t.is_alpha or t.pos_ == "PROPN": continue
                uniq.add(t.lemma_.lower())   # unique words: lemmas, so go/went/gone count once
                L, base = level_of(t, lvl)
                if L:
                    levels[L] += 1; tokens += 1; mlevels[mode][L] += 1
                    if RANK[L] >= 4 and base not in adv:
                        adv[base] = {"word": base, "level": L, "turn": turn, "mode": mode, "sentence": s.text.strip()}
                elif len(t.text) >= 5:
                    w = t.lemma_.lower()
                    # spaCy sometimes invents a lemma ("knackered" -> "knackere"); keep the real word
                    if zipf_frequency and zipf_frequency(w, "en") == 0 and zipf_frequency(t.text.lower(), "en") > 0:
                        w = t.text.lower()
                    off[w] += 1
                    off_mode.setdefault(w, Counter())[mode] += 1
                    off_sent.setdefault(w, s.text.strip())
    cands = []
    for h in hits: cands.append({"i": len(cands), "type": "comeup", **h})
    for a in sorted(adv.values(), key=lambda a: (-RANK[a["level"]], a["word"])):
        cands.append({"i": len(cands), "type": "advanced", **a})
    offlist = []
    for w, c in off.most_common(60):
        z = round(zipf_frequency(w, "en"), 2) if zipf_frequency else None
        offlist.append({"word": w, "count": c, "by_mode": dict(off_mode[w]), "zipf": z,
                        "suggested": suggest_level(z), "sentence": off_sent[w][:300]})
    result = {"tokens": tokens,
              "level_counts": {k: levels[k] for k in RANK},
              "level_counts_by_mode": {m: {k: c[k] for k in RANK} for m, c in mlevels.items()},
              "levels": {k: round(levels[k] / tokens * 100, 1) if tokens else 0 for k in RANK},
              "levels_by_mode": {m: {"tokens": sum(c.values()),
                                     "levels": {k: round(c[k] / sum(c.values()) * 100, 1) if c else 0 for k in RANK}}
                                 for m, c in mlevels.items()},
              "offlist": offlist,
              "mtld": mtld_block(div),
              "lemmas": sorted(uniq),
              "candidates": cands}
    json.dump(result, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"{tokens} words on the CEFR lists · levels: " + " ".join(f"{k} {v}%" for k, v in result["levels"].items()))
    md = result["mtld"]
    print(f'lexical diversity (MTLD): voice {md["voice"]} ({md["words"]["voice"]} words) · typed {md["typed"]} ({md["words"]["typed"]} words) · all {md["all"]}')
    if kept_out: print(f"{kept_out} practised-word hit(s) inside the vocab drill marks kept out (practice, not come-ups)")
    print("VOCAB REVIEW LIST  (index | type | item or word | sentence)")
    for c in cands:
        label = f'#{c["id"]} {c["expr"]}' if c["type"] == "comeup" else f'{c["word"]} ({c["level"]})'
        print(f'{c["i"]:4} | {c["type"]:8} | {label} | {c["turn"]} {c["mode"][0]}: {c["sentence"][:160]}')
    print("OFF-LIST REVIEW  (word | count | zipf -> suggested level | sentence)")
    for o in offlist:
        print(f'  {o["word"]} | {o["count"]} | {o["zipf"]} -> {o["suggested"] or "?"} | {o["sentence"][:140]}')

if __name__ == "__main__":
    main(*sys.argv[1:6])
