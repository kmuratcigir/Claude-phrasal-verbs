"""English Mastery raw counts for one session (added 02.11.26, method "v1 02.11.26").

Scripts count; the Ledger page turns the counts into the Grammar, Vocabulary and Speaking scores
(settings in meta/scoring). No score is stored. Commands:

  python3 mastery.py type session_doc.json
      ERRANT-types every error from its quote and fix ("was -> were" gives R:VERB:SVA) and writes an
      `errant` list on each error. Prints the R:OTHER items for review (only those need an eye):
      put a verdict per error index in mastery_verdicts.json as {"rother": {"<i>": "vocab" |
      "grammar" | "neither"}}. Without a verdict, R:OTHER counts as vocabulary only when the error's
      concept is err_collocation.

  python3 mastery.py build murat_turns.txt session_doc.json [drilled_words.txt] [slot_targets.txt]
      Writes the `mastery` block into session_doc.json: speaking counts (voice turns), grammar and
      vocabulary counts split by voice and typed. Run after session.py, intf.py apply, vt_apply.py
      and `mastery.py type`. Prints a DEPTH REVIEW LIST when meta/scoring asks for Depth checks.
      With depth_verdicts.json ({"T12": true, "T15": false} = developed or not, for the replies
      where you disagree with the rule) it records the agreement in `speaking.depth_check`.

  python3 mastery.py backfill session_doc.json [earlier session docs ...]
      Grammar and vocabulary counts for a past session that has no transcript (speaking stays out).
      Correct concept uses are pooled in old docs, so they are split by voice/typed word share
      (`approx_mode_split`); sentence counts exist only from 28.10.26.

  python3 mastery.py calibrate sessions session_doc.json meta/scoring.json scoring_out.json
      Speaking settings, decided by rule (02.11.26): while meta/scoring says `calibrated: false`, it
      waits for 5 voice sessions with speaking counts (this one included), then sets each measure's
      zero and full point so the median session scores 50 and the second-best scores 75 (at least 15% of the median apart). The Depth
      rule is validated on the first 2 sessions with a `depth_check`: kept if rule and judgement agree
      on 85%+ of replies, otherwise `depth_method` becomes "judged". Writes scoring_out.json only when
      something changes (it goes into the same single save) and prints what it decided.
"""
import difflib, glob, json, os, re, sys
from collections import Counter

GRAMMAR_TYPES = {"PREP", "DET", "VERB:SVA", "VERB:TENSE", "VERB:FORM", "VERB:INFL", "NOUN:NUM",
                 "NOUN:INFL", "PRON", "WO", "MORPH", "CONJ"}          # plus PART when not a phrasal verb
LEX_TYPES = {"R:NOUN", "R:VERB", "R:ADJ", "R:ADV"}                     # plus R:PART (phrasal) and R:OTHER (lexical)
LEX_INTF = {"lex_false_friend", "calque_phrase", "collocation_transfer"}
CHUNK_CONCEPTS = {   # concepts a fixing-slot target drills; their uses in [slot] turns are left out
    "s1": ["b1_present_perfect"], "s2": ["b1_present_perfect"], "s3": ["a2_past_simple"],
    "s4": ["b1_present_perfect", "b2_present_perfect_continuous"], "s5": ["b1_present_perfect"],
    "s6": ["b1_present_perfect"], "s7": ["b1_present_perfect"], "c5": ["b2_still_negative_perfect"],
    "c1": ["err_preposition"], "c2": ["err_preposition"], "c3": [], "c4": [],
}
HESIT = r"\b(?:u+h+m*|u+m+|e+r+m*|hm+|mm+|ah+)\b"
FILLERS = [r"\byou know\b", r"\bi mean\b", r"(?<=,) ?like(?= ?,)", r"\bsort of\b(?= (?:a |the |\w+ing\b|[a-z]+ly\b|like\b|,))",
           r"\bkind of\b(?= (?:\w+ing\b|[a-z]+ly\b|like\b|,))", r"\bbasically\b", r"\bliterally\b"]
CONNECTORS = [  # PDTB-style explicit connectives (+ his tracked ones), longest first when matching
    "on the other hand", "as a result", "in other words", "at the same time", "as long as", "as soon as",
    "even though", "even if", "so that", "in case", "in addition", "for example", "for instance", "in fact",
    "that said", "that's why", "after all", "in spite of", "as well as", "rather than", "provided that",
    "given that", "in the end", "on top of that", "apart from that", "because of that", "in short",
    "and", "but", "or", "so", "because", "since", "although", "though", "while", "whereas", "if", "unless",
    "when", "whenever", "after", "before", "until", "once", "then", "also", "however", "therefore", "thus",
    "otherwise", "instead", "meanwhile", "besides", "moreover", "furthermore", "plus", "still", "yet",
    "finally", "eventually", "afterwards", "despite", "nevertheless", "nonetheless", "consequently",
    "hence", "likewise", "similarly", "overall", "anyway", "whether", "as",
]
LINK_DEPS = {"cc", "mark", "advmod", "prep", "preconj"}

_nlp = _ann = None
def nlp():
    global _nlp
    if _nlp is None:
        import spacy; _nlp = spacy.load("en_core_web_sm")
    return _nlp
def ann():
    global _ann
    if _ann is None:
        import errant; _ann = errant.load("en", nlp())
    return _ann

def load(p):
    d = json.load(open(p, encoding="utf-8")); return d.get("data", d) if isinstance(d, dict) and "data" in d and len(d) <= 3 else d
def dump(d, p):
    t = p + ".tmp"; json.dump(d, open(t, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(t, p)
def norm(t): return re.sub(r"\s+", " ", re.sub(r"[^a-z' ]", " ", (t or "").lower())).strip()

# ---------------------------------------------------------------- ERRANT typing
def errant_types(quote, fix):
    """ERRANT edit types for one error; R:PART becomes R:PART:PV when the particle belongs to a phrasal verb."""
    pairs = []
    for seg in re.split(r"\s*;\s*", fix or ""):
        if "->" in seg:
            o, c = seg.split("->", 1); pairs.append((o.strip(" .\"'"), c.strip(" .\"'")))
    if not pairs and fix:
        pairs = [(quote, fix)]
    out = []
    for o, c in pairs:
        if not o and not c: continue
        a = ann(); po, pc = a.parse(o or "", tokenise=True), a.parse(c or "", tokenise=True)
        for e in a.annotate(po, pc):
            t = e.type
            if t.endswith(":PART"):
                toks = [x for x in list(e.o_toks) + list(e.c_toks)]
                if any(x.lower_ != "to" or x.dep_ == "prt" for x in toks): t = t + ":PV"
            out.append(t)
    return out or ["UNK"]

def kind(err, verdict=None):
    """(grammar?, vocab?) for one typed error."""
    ts = err.get("errant") or []
    g = v = False
    for t in ts:
        op, _, rest = t.partition(":")
        if rest in GRAMMAR_TYPES or rest == "PART": g = True
        if t in LEX_TYPES or t == "R:PART:PV": v = True
        if t == "R:OTHER":
            vd = verdict or ("vocab" if err.get("concept") == "err_collocation" else "neither")
            if vd == "vocab": v = True
            elif vd == "grammar": g = True
    return g, v

def cmd_type(doc_p):
    doc = load(doc_p); rother = []
    for i, e in enumerate(doc.get("errors", [])):
        e["errant"] = errant_types(e.get("quote", ""), e.get("fix", ""))
        if "R:OTHER" in e["errant"]: rother.append((i, e))
    dump(doc, doc_p)
    c = Counter(t for e in doc.get("errors", []) for t in e["errant"])
    print(f"ERRANT: typed {len(doc.get('errors', []))} errors: " + ", ".join(f"{k} {n}" for k, n in c.most_common(12)))
    if rother:
        print("R:OTHER REVIEW (mark only these, in mastery_verdicts.json \"rother\": vocab / grammar / neither):")
        for i, e in rother:
            print(f"  {i} | {e.get('concept')} | {e.get('fix', '')[:70]} | {e.get('quote', '')[:90]}")

# ---------------------------------------------------------------- shared vocab / grammar counting
def lex_problems(doc, mode, verdicts):
    """Union of word-choice slips and Turkish word-choice interference; each problem once."""
    probs = []
    for i, e in enumerate(doc.get("errors", [])):
        if e.get("mode", "voice") != mode: continue
        if kind(e, verdicts.get(str(i)))[1]:
            probs.append({"q": norm(e.get("quote")), "m": e.get("impact") == "m"})
    slips = len(probs)
    for it in (doc.get("interference") or {}).get("items", []):
        if it.get("mode", "voice") != mode or it.get("counted") is False or it.get("type") not in LEX_INTF: continue
        q = norm(it.get("quote"))
        dup = next((p for p in probs[:slips] if q and p["q"] and (q in p["q"] or p["q"] in q or
                    difflib.SequenceMatcher(None, q, p["q"]).ratio() >= 0.75)), None)
        if dup: continue
        probs.append({"q": q, "m": False})   # meaning-changing comes from the error list's impact (as agreed on 02.11)
    return len(probs), sum(1 for p in probs if p["m"])

def grammar_err_sentences_by_quote(doc, mode, verdicts):
    seen = []
    for i, e in enumerate(doc.get("errors", [])):
        if e.get("mode", "voice") != mode or not kind(e, verdicts.get(str(i)))[0]: continue
        q = norm(e.get("quote"))
        if not any(q == s or (len(q) > 12 and (q in s or s in q)) for s in seen): seen.append(q)
    return len(seen)

def adv_levels(words):
    c = Counter(a["level"] for a in words)
    return c.get("B2", 0), c.get("C1", 0), c.get("C2", 0)

# ---------------------------------------------------------------- speaking (voice turns only)
def load_turns(p):
    out, cur = [], None
    for line in open(p, encoding="utf-8"):
        m = re.match(r"^### (T\d+)(?:\s*\[(voice|typed)\])?(.*)$", line.strip())
        if m:
            cur = {"turn": m.group(1), "mode": m.group(2) or "typed", "tags": m.group(3), "text": ""}; out.append(cur)
        elif cur is not None:
            cur["text"] += line
    return out

WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
def speak_counts(text):
    t = " " + text.lower().replace("’", "'") + " "
    words = len(WORD.findall(t))
    hes = len(re.findall(HESIT, t)); t = re.sub(HESIT, " ", t)
    fill = 0
    for f in FILLERS:
        fill += sum(len(WORD.findall(m)) for m in re.findall(f, t))
        t = re.sub(f, " ", t)
    # "sorry" repairs: drop the abandoned fragment (back to the last punctuation, at most 6 words) and "sorry"
    rep_words, repairs = 0, 0
    def _rep(m):
        nonlocal rep_words, repairs
        frag = WORD.findall(m.group(1)); repairs += 1
        if len(frag) <= 6: rep_words += len(frag) + 1; return " , "
        rep_words += 1; return m.group(1) + " , "
    t = re.sub(r"([^.,;?!]*?),? sorry,? (?!for\b|to\b|about\b|i\b)", _rep, t)
    toks = WORD.findall(t)
    clean, rep = [], 0
    i = 0
    while i < len(toks):
        hit = 0
        for n in (3, 2, 1):
            if i + 2 * n <= len(toks) and toks[i:i + n] == toks[i + n:i + 2 * n] and not (n == 1 and toks[i] in ("very", "really", "so", "no", "bye", "ha", "that")):
                hit = n; break
        if hit: rep += hit; i += hit; continue
        clean.append(toks[i]); i += 1
    return {"words": words, "hes": hes, "fill": fill, "rep": rep, "repair": rep_words, "repairs": repairs,
            "clean_text": " ".join(clean), "clean": len(clean)}

def finite_clauses(sdoc):
    n = 0
    for t in sdoc:
        if t.pos_ not in ("VERB", "AUX") or t.dep_ not in ("ROOT", "ccomp", "advcl", "relcl", "conj", "parataxis", "csubj", "xcomp"):
            continue
        if t.pos_ == "AUX" and t.dep_ != "ROOT": continue
        fin = "Fin" in t.morph.get("VerbForm") or any("Fin" in c.morph.get("VerbForm") for c in t.children if c.dep_ in ("aux", "auxpass"))
        if fin: n += 1
    return n

def connectors(sdoc, reply_start=True):
    toks = [t for t in sdoc]; low = [t.lower_ for t in toks]; used = []; i = 0
    first = next((k for k, t in enumerate(toks) if t.is_alpha), 0)
    while i < len(toks):
        hit = None
        for c in sorted(CONNECTORS, key=lambda x: -len(x.split())):
            w = c.replace("'s", " 's").split()
            if low[i:i + len(w)] == w: hit = (c, len(w)); break
        if not hit: i += 1; continue
        c, n = hit; t = toks[i]
        if reply_start and i == first and c in ("so", "and"): i += n; continue   # run-up "so / and"
        head = t.head
        joins = (n > 1) or (t.dep_ in LINK_DEPS and head.pos_ in ("VERB", "AUX")) or (t.dep_ == "cc" and head.pos_ in ("VERB", "AUX", "ADJ"))
        if c in ("like", "as") and t.dep_ != "mark": joins = False
        if c in ("if", "whether", "when", "while", "since", "before", "after", "until", "once", "although", "though", "because", "unless", "whereas") and t.dep_ not in ("mark", "advmod", "cc", "prep"): joins = False
        if joins: used.append(c)
        i += n
    return used

def speaking_block(turns, scoring):
    rule = (scoring.get("speaking") or {}).get("depth_rule") or {"min_clean": 10, "min_clauses": 2}
    minr = (scoring.get("speaking") or {}).get("min_reply_clean", 3)
    S = Counter(); types = set(); per = []
    for tr in turns:
        if tr["mode"] != "voice": continue
        c = speak_counts(tr["text"])
        S["words"] += c["words"]; S["clean_words"] += c["clean"]; S["hesitations"] += c["hes"]
        S["word_fillers"] += c["fill"]; S["repeats"] += c["rep"]; S["repairs"] += c["repairs"]
        if c["clean"] < minr: S["short_replies"] += 1; continue
        sd = nlp()(c["clean_text"])
        cl = finite_clauses(sd); con = connectors(sd)
        dev = c["clean"] >= rule["min_clean"] and cl >= rule["min_clauses"]
        S["replies"] += 1; S["reply_clean_words"] += c["clean"]; S["developed"] += dev; S["connectors"] += len(con)
        types.update(con)
        per.append({"turn": tr["turn"], "clean": c["clean"], "clauses": cl, "dev": dev, "text": c["clean_text"]})
    keys = ["replies", "short_replies", "words", "clean_words", "reply_clean_words", "developed", "connectors",
            "hesitations", "word_fillers", "repeats", "repairs"]
    blk = {k: int(S[k]) for k in keys}; blk["connector_types"] = sorted(types)
    return blk, per

# ---------------------------------------------------------------- build (live wrap-up)
def cmd_build(turns_p, doc_p, drilled_p=None, slot_p=None):
    doc = load(doc_p); here = os.path.dirname(os.path.abspath(doc_p))
    scoring_p = os.path.join(here, "meta", "scoring.json")
    scoring = load(scoring_p) if os.path.exists(scoring_p) else {}
    vp = os.path.join(here, "mastery_verdicts.json")
    verdicts = (load(vp) if os.path.exists(vp) else {}).get("rother", {})
    if any("errant" not in e for e in doc.get("errors", [])):
        sys.exit("STOP: run `python3 mastery.py type session_doc.json` first.")
    turns = load_turns(turns_p)
    drilled = {l.strip().lower() for l in open(drilled_p, encoding="utf-8")} - {""} if drilled_p and os.path.exists(drilled_p) else set()
    targets = [l.strip().split()[0] for l in open(slot_p, encoding="utf-8") if l.strip()] if slot_p and os.path.exists(slot_p) else []
    slot_concepts = sorted({c for t in targets for c in CHUNK_CONCEPTS.get(t, [])})
    words = {m: (doc.get("by_mode") or {}).get(m, {}).get("words", 0) for m in ("voice", "typed")}

    # grammar: concept counts per mode from the candidates file, slot targets left out in [slot] turns
    cands = load(os.path.join(here, "candidates.json"))
    v = load(os.path.join(here, "verdicts.json"))
    drop = {int(x) for x in v.get("drop", [])}; err = {int(k) for k in v.get("error", {})}
    rel = {int(k): t for k, t in v.get("relabel", {}).items()}; caught = {int(x) for x in v.get("caught", [])}
    slot_turns = {t["turn"] for t in turns if "[slot]" in t["tags"]}
    conc = {"voice": {}, "typed": {}}; excluded = Counter()
    def add(mode, cid, ok, w=1):
        c = conc[mode].setdefault(cid, {"c": 0, "e": 0}); c["c" if ok else "e"] += (1 if ok else w)
    for c in cands["candidates"]:
        i = c["i"]
        if i in drop: continue
        cid = rel.get(i, c["concept"]); ok = not (i in err or c["kind"] == "error" or cid.startswith("err_"))
        if c.get("turn") in slot_turns and cid in slot_concepts: excluded[cid] += 1; continue
        add(c.get("mode", "typed"), cid, ok, 0.5 if i in caught else 1)
    for x in v.get("extra", []):
        cid = x["concept"]; ok = x.get("result", "error") == "correct"
        if x.get("turn") in slot_turns and cid in slot_concepts: excluded[cid] += 1; continue
        add(x.get("mode", "typed"), cid, ok, 0.5 if x.get("caught") else 1)

    sent = sentence_counts(turns, doc, verdicts)
    grammar = {m: {"concepts": conc[m], "sentences": sent[m][0], "grammar_err_sentences": sent[m][1]} for m in ("voice", "typed")}
    grammar["drilled_excluded"] = [f"{k} ({n})" for k, n in sorted(excluded.items())]

    # vocabulary: advanced words per mode (first use), drilled words left out when only used inside the drill
    adv_all = (doc.get("vocab") or {}).get("advanced", [])
    drill_text = norm(" ".join(t["text"] for t in turns if "[vocab-drill]" in t["tags"]))
    free_text = {m: norm(" ".join(t["text"] for t in turns if t["mode"] == m and "[vocab-drill]" not in t["tags"])) for m in ("voice", "typed")}
    vocab = {"drilled_excluded": []}
    uniq = uniques(turns)
    for m in ("voice", "typed"):
        adv = []
        for a in adv_all:
            w = a["word"].lower()
            if re.search(rf"\b{re.escape(w)}", free_text[m]): adv.append(a)
            elif w in drilled and re.search(rf"\b{re.escape(w)}", drill_text) and m == "voice": vocab["drilled_excluded"].append(w)
        b2, c1, c2 = adv_levels(adv); n, mm = lex_problems(doc, m, verdicts)
        vocab[m] = {"unique": uniq[m], "b2": b2, "c1": c1, "c2": c2, "adv_words": sorted({a["word"].lower() for a in adv}),
                    "lex_problems": n, "lex_m": mm, "words": words[m]}
    vocab["drilled_excluded"] = sorted(set(vocab["drilled_excluded"]))

    sp, per = speaking_block(turns, scoring)
    spc = scoring.get("speaking") or {}
    dv_p = os.path.join(here, "depth_verdicts.json")
    if spc.get("depth_method") == "judged" or (spc.get("depth_validation") or {}).get("open", True):
        if os.path.exists(dv_p):
            dv = load(dv_p); agree = sum(1 for r in per if dv.get(r["turn"], r["dev"]) == r["dev"])
            if spc.get("depth_method") == "judged": sp["developed"] = sum(1 for r in per if dv.get(r["turn"], r["dev"]))
            sp["depth_check"] = {"n": len(per), "agree": agree}
            print(f"DEPTH CHECK: rule and judgement agree on {agree} of {len(per)} replies ({round(100 * agree / max(1, len(per)))}%)")
        else:
            print("DEPTH REVIEW LIST (rule: 10+ clean words and 2+ finite clauses = developed). Read each reply; write")
            print("depth_verdicts.json with ONLY the replies where you disagree, e.g. {\"T12\": true, \"T15\": false}, then rerun build.")
            for r in per: print(f"  {r['turn']} | {'DEV' if r['dev'] else 'no '} | {r['clean']}w {r['clauses']}cl | {r['text'][:110]}")
    doc["mastery"] = {"speaking": sp, "grammar": grammar, "vocab": vocab, "method": "v1 02.11.26"}
    dump(doc, doc_p)
    g = grammar["voice"]; vv = vocab["voice"]
    print(f"MASTERY: speaking {sp['replies']} replies, {sp['clean_words']} clean of {sp['words']} words, "
          f"{sp['developed']} developed, {sp['connectors']} connectors ({len(sp['connector_types'])} kinds), "
          f"fillers {sp['hesitations']}+{sp['word_fillers']}; grammar voice {g['sentences']} sentences, "
          f"{g['grammar_err_sentences']} with a grammar error; vocab voice {vv['unique']} words, B2+ {vv['b2']}/{vv['c1']}/{vv['c2']}, "
          f"{vv['lex_problems']} word-choice problems ({vv['lex_m']} meaning-changing)")

def uniques(turns):
    """Different words (lemmas, letters only, names and fillers out), as lex_apply.py counts them."""
    out = {}
    for m in ("voice", "typed"):
        text = " ".join(speak_counts(t["text"])["clean_text"] for t in turns if t["mode"] == m)
        if not text.strip(): out[m] = 0; continue
        lem = {t.lemma_.lower() for t in nlp()(text) if t.is_alpha and t.pos_ not in ("PROPN", "INTJ", "NUM", "X")}
        out[m] = len(lem)
    return out

def sentence_counts(turns, doc, verdicts):
    """Sentences of 3+ tokens per mode, and those holding at least one grammar-type error."""
    res = {}
    for m in ("voice", "typed"):
        sents = []
        for t in turns:
            if t["mode"] != m: continue
            for s in nlp()(speak_counts(t["text"])["clean_text"]).sents:
                if len(s) >= 3: sents.append(norm(s.text).split())
        hit, extra = set(), 0
        for i, e in enumerate(doc.get("errors", [])):
            if e.get("mode", "voice") != m or not kind(e, verdicts.get(str(i)))[0]: continue
            q = norm(e.get("quote")).split()
            best, sc = None, 0.0
            for k, w in enumerate(sents):
                s = 1.0 if " ".join(q) in " ".join(w) else difflib.SequenceMatcher(None, q, w).ratio()
                if s > sc: best, sc = k, s
            if best is None or sc < 0.6: extra += 1
            else: hit.add(best)
        res[m] = (len(sents), len(hit) + extra)
    return res

# ---------------------------------------------------------------- backfill (past sessions, no transcript)
def cmd_backfill(doc_p, *_):
    doc = load(doc_p)
    for e in doc.get("errors", []):
        if "errant" not in e: e["errant"] = errant_types(e.get("quote", ""), e.get("fix", ""))
    words = {m: (doc.get("by_mode") or {}).get(m, {}).get("words", 0) for m in ("voice", "typed")}
    tot = sum(words.values()) or 1
    conc = {"voice": {}, "typed": {}}
    for cid, c in (doc.get("concepts") or {}).items():
        ev = sum(x.get("weight", 1) for x in doc.get("errors", []) if x.get("concept") == cid and x.get("mode", "voice") == "voice")
        et = c.get("error", 0) - ev
        cv = round(c.get("correct", 0) * words["voice"] / tot, 2); ct = round(c.get("correct", 0) - cv, 2)
        if cv or ev: conc["voice"][cid] = {"c": cv, "e": ev}
        if ct or et > 0: conc["typed"][cid] = {"c": ct, "e": max(0, et)}
    s = doc.get("sentences") or {}
    grammar = {"voice": {"concepts": conc["voice"], "sentences": s.get("voice"),
                         "grammar_err_sentences": grammar_err_sentences_by_quote(doc, "voice", {}) if s.get("voice") else None},
               "typed": {"concepts": conc["typed"], "sentences": None, "grammar_err_sentences": None},
               "drilled_excluded": [], "approx_mode_split": words["typed"] > 0}
    v = doc.get("vocab") or {}
    adv = v.get("advanced", []); b2, c1, c2 = adv_levels(adv)
    nv, mv = lex_problems(doc, "voice", {}); nt, mt = lex_problems(doc, "typed", {})
    vocab = {"voice": {"unique": (v.get("unique") or {}).get("session"), "b2": b2, "c1": c1, "c2": c2,
                       "adv_words": sorted({a["word"].lower() for a in adv}), "lex_problems": nv, "lex_m": mv, "words": words["voice"]},
             "typed": {"unique": None, "b2": None, "c1": None, "c2": None, "adv_words": [], "lex_problems": nt, "lex_m": mt, "words": words["typed"]},
             "drilled_excluded": [], "approx_mode_split": words["typed"] > 0}
    doc["mastery"] = {"speaking": None, "grammar": grammar, "vocab": vocab, "method": "v1 02.11.26", "backfilled": "02.11.2026"}
    dump(doc, doc_p)
    return doc

# ---------------------------------------------------------------- calibration (speaking settings, by rule)
def cmd_calibrate(sdir, doc_p, sc_p, out_p):
    sc = load(sc_p); doc = load(doc_p); P = sc["speaking"]; changed = False
    if os.path.exists(out_p): os.remove(out_p)
    docs = {}
    for p in sorted(glob.glob(os.path.join(sdir, "*.json"))):
        d = load(p); docs[os.path.basename(p)[:-5]] = d
    docs["__today__"] = doc
    def dk(d): dd, mm, yy = d["date"].split("."); return yy + mm + dd
    sp = sorted(((dk(d), k, d["mastery"]["speaking"]) for k, d in docs.items()
                 if (d.get("mastery") or {}).get("speaking") and d["mastery"]["speaking"].get("replies")), key=lambda x: x[:2])
    seen = {}
    for key, k, b in sp: seen[(key, b.get("words"))] = (key, k, b)   # same chat saved twice counts once
    sp = sorted(seen.values(), key=lambda x: x[:2])
    msgs = []
    V = P.get("depth_validation") or {}
    if P.get("depth_method", "rule") == "rule" and V.get("open", True):
        checks = [(k, b["depth_check"]) for _, k, b in sp if b.get("depth_check")]
        if len(checks) >= V.get("sessions_needed", 2):
            n = sum(c["n"] for _, c in checks); a = sum(c["agree"] for _, c in checks)
            ok = n and a / n >= V.get("agree_min", 0.85)
            V.update({"open": False, "checks": [{"session": k, **c} for k, c in checks], "agreement": round(a / n, 3) if n else None})
            P["depth_validation"] = V; P["depth_method"] = "rule" if ok else "judged"; changed = True
            msgs.append(f"DEPTH: rule and careful reading agreed on {a} of {n} replies ({round(100 * a / max(1, n))}%): "
                        + ("the rule stays." if ok else "below 85%, so from now on Claude judges Depth in the check (depth_method: judged)."))
        else:
            msgs.append(f"DEPTH: validation {len(checks)} of {V.get('sessions_needed', 2)} sessions done.")
    C = P.get("calibration") or {}
    if not P.get("calibrated"):
        need = C.get("sessions_needed", 5)
        if len(sp) >= need:
            use = sp[:need]; vals = {"flow": [], "depth": [], "cohesion": [], "fillers": []}
            for _, _, b in use:
                vals["flow"].append((b.get("reply_clean_words") or b["clean_words"]) / b["replies"])
                vals["depth"].append(100 * b["developed"] / b["replies"])
                vals["cohesion"].append(100 * b["connectors"] / max(1, b["clean_words"]))
                vals["fillers"].append(100 * (b["hesitations"] + b["word_fillers"]) / max(1, b["words"]))
            for k, xs in vals.items():
                xs = sorted(xs); med = xs[len(xs) // 2]
                second = xs[1] if k == "fillers" else xs[-2]          # second-best day (fillers: lower is better)
                d = max(abs(second - med), 0.15 * abs(med), 0.01)
                if k == "fillers": z, f = med + 2 * d, med - 2 * d
                else: z, f = med - 2 * d, med + 2 * d
                P[k]["zero"], P[k]["full"] = round(z, 2), round(f, 2)
                msgs.append(f"CALIBRATED {k}: median {med:.1f} -> 50, second-best {second:.1f} -> 75; zero {z:.1f}, full {f:.1f}")
            C.update({"done_on": doc["date"], "from_sessions": [k if k != "__today__" else "this session" for _, k, _ in use]})
            P["calibration"] = C; P["calibrated"] = True; changed = True
        else:
            msgs.append(f"SPEAKING: calibrating, {len(sp)} of {need} sessions with speaking counts so far (no Speaking score until then).")
    if changed:
        sc["speaking"] = P; dump(sc, out_p); msgs.append(f"wrote {out_p}: stage it as meta/scoring")
    print("\n".join(msgs))

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("type", "build", "backfill", "calibrate"): sys.exit(__doc__)
    {"type": lambda: cmd_type(a[1]), "build": lambda: cmd_build(*a[1:5]), "backfill": lambda: [cmd_backfill(p) for p in a[1:]],
     "calibrate": lambda: cmd_calibrate(*a[1:5])}[a[0]]()
