#!/usr/bin/env python3
"""Preposition accuracy for the naturalness check (draft, 16.10.26 — not installed yet).

Finds every word + preposition pair Murat says, marks each one right or wrong against the
check's own preposition flags, and adds up accuracy for the watch list, the Turkish-source
groups and the preposition chips. The script finds and counts; Claude has already judged the
slips (the flags), so nothing here decides what is wrong on its own.

  python3 preps.py find  murat_turns.txt cands.json
  python3 preps.py seed  sessions_dir watch.json               (watch list from past slips)
  python3 preps.py score cands.json flags.json watch.json out.json

flags.json: [{"turn": "T12", "quote": "...", "fix": "...", "turkish": "...", "mode": "voice"}]
 = the session's preposition slips (interference preposition_case + err_preposition), as the
 check already writes them. A use is wrong when its preposition falls inside a flagged quote;
 a flag with no preposition inside (a dropped one, "hang out our friends") is added as a wrong use.
Row key = the word Murat said (Murat, 16.10.26), not the word in the fix.
"""
import json, re, sys, glob, os, collections
import spacy

nlp = spacy.load("en_core_web_sm")

FILLERS = re.compile(r"\b(?:uh|um|erm|er|hmm|mm)\b,?|\bsorry\b,?(?!\s+(?:for|about|if|that|to)\b)", re.I)
def clean(t):
    t = FILLERS.sub(" ", t); t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\b(\w+)(?:,?\s+\1\b)+", r"\1", t, flags=re.I)
    return t.strip()

def read_turns(path):
    turns, cur = [], None
    for line in open(path, encoding="utf-8"):
        m = re.match(r"###\s*(T\d+)\s*\[(voice|typed)\]", line)
        if m: cur = {"turn": m.group(1), "mode": m.group(2), "text": ""}; turns.append(cur)
        elif cur is not None: cur["text"] += line
    for t in turns: t["text"] = clean(t["text"])
    return turns

# generic heads tell nothing about which preposition is right ("be in", "go to"): counted overall, never watch-list keys
GENERIC = {"be", "have", "do", "get", "go", "come", "make", "take", "say", "tell", "think", "know", "see", "want",
           "need", "try", "let", "use", "keep", "give", "lot", "kind", "sort", "part", "one", "all", "some", "most", "way", "thing"}
MULTI = {("out", "of"), ("on", "to"), ("instead", "of"), ("because", "of"), ("due", "to"), ("according", "to"),
         ("apart", "from"), ("as", "for"), ("in", "terms"), ("prior", "to"), ("regardless", "of")}
TIME = re.compile(r"^(monday|tuesday|wednesday|thursday|friday|saturday|sunday|weekends?|morning|afternoon|evening|night|day|days|week|month|year|time|times|minute|minutes|hour|hours|beginning|end|moment|today|tomorrow|christmas|weekend|\d.*|january|february|march|april|may|june|july|august|september|october|november|december)$", re.I)

TIMEP = {"at", "on", "in", "for", "since", "during", "over", "by", "until"}
def pairs(doc):
    """Every preposition with the word that decides it. Infinitive 'to' and phrasal-verb particles are never ADP+prep."""
    out = []
    for t in doc:
        if t.pos_ not in ("ADP", "SCONJ"): continue
        if t.dep_ not in ("prep", "dative", "agent") and not (t.dep_ == "ROOT" and t.pos_ == "ADP"): continue   # ROOT: a quote with no verb
        head = t.head
        prev = doc[t.i - 1] if t.i else None
        word = t.text.lower()
        if prev is not None and (prev.text.lower(), word) in MULTI:
            word = prev.text.lower() + " " + word
        nouns = [x for x in t.subtree if x.i > t.i and x.pos_ in ("NOUN", "PROPN", "NUM")]
        objs = nouns[:1] or [c for c in t.children if c.dep_ in ("pobj", "pcomp")]
        obj = objs[0].text if objs else ""
        # time phrases belong to the time word ("in the last minute" -> minute), only for the time prepositions
        lemma = objs[0].lemma_.lower() if objs and TIME.match(obj) and word in TIMEP else head.lemma_.lower()
        out.append({"head": head.text, "hidx": head.i, "lemma": lemma, "pos": head.pos_, "prep": word,
                    "obj": obj, "start": t.idx, "end": t.idx + len(t.text)})
    return out

def cmd_find(turns_path, out_path):
    cands = []
    for tr in read_turns(turns_path):
        for p in pairs(nlp(tr["text"])):
            p.update(turn=tr["turn"], mode=tr["mode"]); cands.append(p)
    tt = read_turns(turns_path)
    json.dump({"turns": {t["turn"]: t["text"] for t in tt}, "modes": {t["turn"]: t["mode"] for t in tt}, "cands": cands},
              open(out_path, "w"), ensure_ascii=False, indent=1)
    print(len(cands), "word + preposition pairs found")

# ---- Turkish source -> group (same nine groups as the mockup)
def group_of(turkish, fix, quote):
    t = (turkish or "").lower(); f = (fix or "").lower()
    fd = nlp(f); qd = nlp((quote or "").lower())
    fp = [p for p in pairs(fd)]
    if any(TIME.match(p["obj"] or "") for p in fp) or re.search(r"\b(in|at|on) (the )?(beginning|end|last minute|weekend|night|christmas|this time)", f): return "time"
    if re.search(r"hakkında|konu", t): return "hakkinda"
    if "için" in t: return "icin"
    if re.search(r"\bile\b|-le\b|-la\b", t): return "ile"
    if re.search(r"-d[ae]n|beri", t): return "den"
    if re.search(r"-d[ae]\b|-t[ae]\b|locative", t): return "de"
    if re.search(r"-[ea]\b|dative|-y[ea]|doğru|karşı", t): return "e"
    if len([p for p in pairs(qd)]) > len(fp): return "zero"
    return "other"

PREPS = {"about","above","across","after","against","along","among","around","as","at","before","behind","below","beneath","beside",
         "between","beyond","by","despite","during","for","from","in","inside","into","like","near","of","off","on","onto","out","over",
         "past","since","than","through","throughout","to","towards","toward","under","until","upon","with","within","without"}
def pw(text):
    """Prepositions in a short text; infinitive 'to' (want to go) is not one."""
    return [t.text.lower() for t in nlp(text or "") if t.text.lower() in PREPS and t.pos_ != "PART"
            and not (t.text.lower() == "to" and t.i + 1 < len(t.doc) and t.doc[t.i + 1].pos_ in ("VERB", "AUX"))]
def right_of(quote, fix):
    """The preposition the fix brings in (a plain word diff, so short fixes like 'at the beginning' work); none = ∅."""
    said = set(pw(quote)); new = [w for w in pw(fix) if w not in said]
    return new[0] if new else "∅"

# verbs that take their object directly: every use counts as a "no preposition" decision, so a right
# "discuss the plan" is counted too, not only the wrong "discuss about" (16.10.26)
ZERO = {"discuss", "mention", "contact", "join", "approach", "message", "research", "seek", "chase", "enter", "marry",
        "attend", "answer", "lack", "resemble", "accompany", "promise", "fit", "email", "phone", "text", "visit", "reach", "ask"}

def key_of(quote, fix):
    """The word Murat said that decides the preposition (option A, 16.10.26).
    1) the preposition he said that the fix changes -> the word it hangs on (a time word wins: "in the last minute" -> minute)
    2) a dropped preposition -> the word in the fix it hangs on, if he said that word
    3) otherwise the first content word he said."""
    q = nlp(quote or ""); f = nlp(fix or "")
    if len(q) and q[0].text.islower() and q[0].pos_ in ("PROPN", "NOUN"):   # "bridge the holiday..." read as a name: give it a subject
        q = nlp("I " + quote)
    qp, fp = pairs(q), pairs(f)
    right = right_of(quote, fix)
    fixw = set(pw(fix))
    changed = [p for p in qp if p["prep"].split()[-1] not in fixw]
    if changed and re.search(r"\bsame\b", (quote or "").lower()): return "same", right   # the same as / the same about
    for p in changed:
        if p["lemma"] in PREPS: continue                      # a preposition is never the deciding word
        if p["lemma"] not in GENERIC or TIME.match(p["obj"] or ""): return p["lemma"], right
    qlem = {t.lemma_.lower() for t in q}
    for p in fp:
        if p["lemma"] in qlem and p["lemma"] not in GENERIC: return p["lemma"], right
    zero = [t.lemma_.lower() for t in q if t.lemma_.lower() in ZERO]
    if zero: return zero[0], right
    for p in qp:
        if p["lemma"] not in GENERIC and p["lemma"] not in PREPS: return p["lemma"], right
    content = [t for t in q if t.pos_ in ("VERB", "ADJ", "NOUN") and t.lemma_.lower() not in GENERIC and t.lemma_.lower() not in PREPS]
    return (content[0].lemma_.lower() if content else None), right

def cmd_seed(sess_dir, out_path):
    rows = {}
    for f in sorted(glob.glob(os.path.join(sess_dir, "*.json"))):
        d = json.load(open(f)); d = d.get("data", d)
        items = [dict(quote=i["quote"], fix=i.get("fix", ""), turkish=i.get("turkish", "")) for i in d["interference"]["items"] if i.get("type") == "preposition_case"]
        norm = lambda x: re.sub(r"[^a-z ]", "", (x or "").lower())
        seen = [norm(i["quote"]) for i in items]
        for e in d["errors"]:
            if e["concept"] != "err_preposition": continue
            q = norm(e["quote"])
            if any(x and (x in q or q in x) for x in seen): continue   # same slip, already logged as interference
            items.append(dict(quote=e["quote"], fix=e.get("fix", "").split("->")[-1], turkish=""))
        for it in items:
            k, right = key_of(it["quote"], it["fix"])
            if not k: continue
            r = rows.setdefault(k, {"word": k, "right": collections.Counter(), "groups": collections.Counter(), "slips": 0, "examples": []})
            r["slips"] += 1; r["right"][right] += 1; r["groups"][group_of(it["turkish"], it["fix"], it["quote"])] += 1
            if len(r["examples"]) < 6: r["examples"].append({"date": d.get("date", ""), "said": it["quote"][:120], "fix": it["fix"][:120]})
    out = []
    for r in rows.values():
        g = [x for x, _ in r["groups"].most_common() if x != "other"]
        out.append({"word": r["word"], "right": r["right"].most_common(1)[0][0], "group": g[0] if g else "other",
                    "slips": r["slips"], "examples": r["examples"]})
    out.sort(key=lambda r: -r["slips"])
    json.dump(out, open(out_path, "w"), ensure_ascii=False, indent=1)
    print(len(out), "watch-list rows from past slips")

CHIP = {"at": "at", "on": "on", "in": "in", "to": "to", "into": "into", "of": "of", "for": "for", "with": "with", "about": "about",
        "from": "from", "as": "as", "by": "by", "over": "over", "towards": "towards", "toward": "towards", "out of": "out of", "on to": "on to",
        "onto": "on to", "during": "along / during", "along": "along / during", "through": "through", "across": "across", "within": "within",
        "above": "above", "below": "below / under", "under": "below / under", "beyond": "beyond", "among": "among / between", "between": "among / between",
        "throughout": "throughout", "upon": "upon", "despite": "despite", "instead of": "instead of", "due to": "due to", "according to": "according to"}
def chip_of(prep, obj):
    if prep in ("at", "on", "in") and TIME.match(obj or ""): return "at / on / in (time)"
    return CHIP.get(prep, prep)

def cmd_score(cands_path, flags_path, watch_path, out_path):
    C = json.load(open(cands_path)); turns, cands = C["turns"], C["cands"]
    flags = json.load(open(flags_path)); watch = {r["word"]: r for r in json.load(open(watch_path))}
    for c in cands: c["ok"] = True
    extra = []
    for fl in flags:
        tid = fl.get("turn") or next((t for t, x in turns.items() if fl["quote"].lower() in x.lower()), None)
        if not tid: fl["unmatched"] = True; continue
        fl["turn"] = tid; text = turns[tid].lower(); s = text.find(fl["quote"].lower())
        e = s + len(fl["quote"])
        inside = [c for c in cands if c["turn"] == tid and s <= c["start"] < e]
        k, right = key_of(fl["quote"], fl["fix"])
        grp = group_of(fl.get("turkish", ""), fl["fix"], fl["quote"])
        fixw = set(pw(fl["fix"]))
        wrong = ([c for c in inside if c["prep"].split()[-1] not in fixw] or inside)[:1]   # one slip per flag: the preposition that changed
        if inside:
            for c in wrong: c.update(ok=False, right=right, flag=fl["quote"], fix=fl["fix"], group=grp)
        else:
            extra.append({"turn": tid, "mode": fl.get("mode") or "voice", "lemma": k, "prep": "∅", "obj": "", "ok": False,
                          "right": right, "flag": fl["quote"], "fix": fl["fix"], "group": grp, "dropped": True})
        if k and k not in watch:   # a new slip adds its word to the watch list
            watch[k] = {"word": k, "right": right, "group": grp, "slips": 0, "examples": [], "new": True}
        if k: watch[k]["slips"] += 1
    # right "no preposition" uses: every use of a ZERO verb on the watch list that has no preposition after it
    zero_watch = {w for w, r in watch.items() if r.get("right") == "∅" and w in ZERO}
    seen_heads = {(c["turn"], c.get("hidx")) for c in cands}
    flagged_turn_words = {(u["turn"], u.get("lemma")) for u in extra}
    for tid, text in turns.items():
        if C.get("modes", {}).get(tid, "voice") != "voice": continue
        for t in nlp(text):
            L = t.lemma_.lower()
            if L in zero_watch and t.pos_ == "VERB" and (tid, t.i) not in seen_heads and (tid, L) not in flagged_turn_words:
                extra.append({"turn": tid, "mode": "voice", "lemma": L, "prep": "∅", "obj": "", "ok": True, "right": "∅"})
    uses = [c for c in cands + extra if c.get("mode") == "voice"]
    def acc(xs): return (round(sum(x["ok"] for x in xs) / len(xs) * 100), len(xs)) if xs else (None, 0)
    wl = [u for u in uses if u.get("lemma") in watch]
    for u in wl: u.setdefault("group", watch[u["lemma"]]["group"])
    by_g = collections.defaultdict(list); by_w = collections.defaultdict(list); by_c = collections.defaultdict(list)
    for u in wl: by_g[u["group"]].append(u); by_w[u["lemma"]].append(u)
    for u in uses:
        need = (u["prep"] if u["prep"] != "∅" else "∅") if u["ok"] else u.get("right", "∅")
        by_c["∅ no preposition" if need == "∅" else chip_of(need, u.get("obj"))].append(u)
    out = {"all": acc(uses), "watch": acc(wl),
           "groups": {g: acc(v) for g, v in sorted(by_g.items(), key=lambda kv: -len(kv[1]))},
           "chips": {c: acc(v) for c, v in sorted(by_c.items(), key=lambda kv: -len(kv[1]))},
           "words": {w: acc(v) for w, v in sorted(by_w.items(), key=lambda kv: -len(kv[1]))},
           "wrong": [{k: u.get(k) for k in ("turn", "lemma", "prep", "right", "flag", "fix", "group", "dropped")} for u in uses if not u["ok"]],
           "unmatched_flags": [f for f in flags if f.get("unmatched")],
           "new_words": sorted(w for w, r in watch.items() if r.get("new"))}
    json.dump(out, open(out_path, "w"), ensure_ascii=False, indent=1)
    print("all", out["all"], "| watch list", out["watch"], "| wrong", len(out["wrong"]), "| new words", len(out["new_words"]))

if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    {"find": cmd_find, "seed": cmd_seed, "score": cmd_score}[cmd](*a)
