#!/usr/bin/env python3
"""Preposition accuracy for the naturalness check (16.10.26).

Finds every word + preposition pair Murat says, marks each one right or wrong against the
check's own preposition flags, and adds up accuracy for the watch list, the Turkish-source
groups and the preposition chips. The script finds and counts; Claude has already judged the
slips (the flags), so nothing here decides what is wrong on its own.

  python3 preps.py find  murat_turns.txt cands.json
  python3 preps.py seed  sessions_dir watch.json               (watch list from past slips)
  python3 preps.py score cands.json flags.json watch.json out.json
  python3 preps.py run   murat_turns.txt session_doc.json meta/prep_watch.json prep_watch_out.json <doc_id>
                                                              (the naturalness check's step: all of the above, fails softly)

flags.json: [{"turn": "T12", "quote": "...", "fix": "...", "turkish": "...", "mode": "voice"}]
 = the session's preposition slips (interference preposition_case + err_preposition), as the
 check already writes them. A use is wrong when its preposition falls inside a flagged quote;
 a flag with no preposition inside (a dropped one, "hang out our friends") is added as a wrong use.
Row key = the word Murat said (Murat, 16.10.26), not the word in the fix.
Voice and typed turns both count, and every figure is also given per mode.
A word joins the list on its second slip; after one slip it waits (status "waiting"), and its uses count only in the overall figure.
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

DATE = re.compile(r"^(\d.*|january|february|march|april|may|june|july|august|september|october|november|december)$", re.I)
PRT = {"back", "up", "out", "off", "down", "away", "over"}
TIMEP = {"at", "on", "in", "for", "since", "during", "over", "by", "until"}
def pairs(doc):
    """Every preposition with the word that decides it. Infinitive 'to' and phrasal-verb particles are never ADP+prep."""
    out = []
    for t in doc:
        if t.pos_ not in ("ADP", "SCONJ"): continue
        if t.dep_ not in ("prep", "dative", "agent") and not (t.dep_ == "ROOT" and t.pos_ == "ADP"): continue   # ROOT: a quote with no verb
        if t.pos_ == "SCONJ" and not any(c.dep_ in ("pobj", "pcomp") for c in t.children): continue   # "because I", "as I said": a conjunction, not a preposition
        head = t.head
        prev = doc[t.i - 1] if t.i else None
        word = t.text.lower()
        if prev is not None and (prev.text.lower(), word) in MULTI:
            word = prev.text.lower() + " " + word
        nouns = [x for x in t.subtree if x.i > t.i and x.pos_ in ("NOUN", "PROPN", "NUM")]
        objs = nouns[:1] or [c for c in t.children if c.dep_ in ("pobj", "pcomp")]
        obj = objs[0].text if objs else ""
        # time phrases belong to the time word ("in the last minute" -> minute), only for the time prepositions
        if objs and TIME.match(obj) and word in TIMEP:
            lemma = "dates" if DATE.match(obj) else objs[0].lemma_.lower()    # "at 28", "in 29th October" -> one dates row
        elif head.pos_ in ("ADV", "ADP") and head.text.lower() in PRT and head.head.pos_ == "VERB":
            lemma = head.head.lemma_.lower() + " " + head.text.lower()       # "look back to" -> look back
        else:
            prt = [c.text.lower() for c in head.children if c.dep_ == "prt" and c.text.lower() in PRT and c.i < t.i]
            lemma = head.lemma_.lower() + (" " + prt[0] if prt and head.pos_ == "VERB" else "")   # "looking them up from" -> look up
        if word not in PREPS and word not in {" ".join(m) for m in MULTI} or word in ("out", "up"): continue   # particles and stray tags ("@", "vs") are not counted
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
    said = collections.Counter(pw(quote)); new = []
    for w in pw(fix):                                  # a count diff: "knowledge for some of" -> "knowledge of some of" brings in one "of"
        if said[w]: said[w] -= 1
        else: new.append(w)
    return new[0] if new else "∅"

# verbs that take their object directly: every use counts as a "no preposition" decision, so a right
# "discuss the plan" is counted too, not only the wrong "discuss about" (16.10.26)
ZERO = {"discuss", "mention", "contact", "join", "approach", "message", "research", "seek", "chase", "enter", "marry",
        "attend", "answer", "lack", "resemble", "accompany", "promise", "fit", "email", "phone", "text", "visit", "reach", "ask"}

def keyable(lemma):
    return bool(lemma) and re.match(r"^[a-z][a-z ]*$", lemma) and lemma not in PREPS and lemma not in NONKEY

NONKEY = {"i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "this", "that", "these", "those", "there", "here",
          "actually", "really", "just", "also", "sorry", "so", "very", "even", "still"}
# keys that said nothing about the preposition when the seed was cleaned by hand (16.10.26): never a row; the slip
# still counts in "all". ALIAS merges the same word seen two ways.
SKIP_KEYS = {"up", "something", "people", "deal", "work", "certain", "co", "one", "old", "last", "big", "mini", "personal", "baby",
             "business", "lot", "make", "some", "skill", "thread", "analysis", "deep", "fake", "wife", "ceo", "sometime", "case", "high",
             "family", "expensive", "smoke", "plate", "tunnel", "mid", "second", "usual", "annual", "side", "company", "connection",
             "dinner", "game", "park", "window", "year", "scene", "source", "original", "shape", "construction", "clear", "meeting",
             "conversation", "lucky", "trickiest", "attach"}
ALIAS = {"well": "good", "better": "good", "rooted": "root", "swap over": "swap", "rid": "swap", "right": "path", "committed": "commit",
         "return back": "return", "datum": "receive"}
def key_of(quote, fix):
    k, right = _key_of(quote, fix)
    k = ALIAS.get(k, k)
    return (None if k in SKIP_KEYS else k), right

def _key_of(quote, fix):
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
        if not keyable(p["lemma"]): continue                  # a preposition, pronoun or filler is never the deciding word
        if p["lemma"] not in GENERIC or TIME.match(p["obj"] or ""): return p["lemma"], right
    qlem = {t.lemma_.lower() for t in q}
    for p in fp:
        if p["lemma"].split()[0] in qlem and p["lemma"] not in GENERIC and keyable(p["lemma"]): return p["lemma"], right
    zero = [t.lemma_.lower() for t in q if t.lemma_.lower() in ZERO]
    if zero: return zero[0], right
    for p in qp:
        if p["lemma"] not in GENERIC and keyable(p["lemma"]): return p["lemma"], right
    content = [t for t in q if t.pos_ in ("VERB", "ADJ", "NOUN") and t.lemma_.lower() not in GENERIC and keyable(t.lemma_.lower())]
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
        out.append({"word": r["word"], "right": " / ".join([x for i, (x, c) in enumerate(r["right"].most_common(2)) if i == 0 or c >= 2]), "group": g[0] if g else "other",
                    "slips": r["slips"], "status": "on" if r["slips"] >= 2 else "waiting", "examples": r["examples"]})
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
        q = clean(fl["quote"]).lower().strip(" .,")        # turns are cleaned of fillers, so the quote is too
        order = ([fl["turn"]] if fl.get("turn") in turns else []) + list(turns)
        tid = next((t for t in order if q and q in turns[t].lower()), None)
        if not tid:   # the check saw the slip but its quote isn't in the turns (paraphrased or cut): still one wrong use
            fl["unmatched"] = True; k, right = key_of(fl["quote"], fl["fix"])
            extra.append({"turn": None, "mode": fl.get("mode") or "voice", "lemma": k, "prep": "?", "obj": "", "ok": False, "right": right,
                          "flag": fl["quote"], "fix": fl["fix"], "group": group_of(fl.get("turkish", ""), fl["fix"], fl["quote"])})
            if k in watch: watch[k]["slips"] += 1; watch[k]["changed"] = True
            continue
        fl["turn"] = tid; s = turns[tid].lower().find(q); e = s + len(q)
        inside = [c for c in cands if c["turn"] == tid and s <= c["start"] < e]
        k, right = key_of(fl["quote"], fl["fix"])
        grp = group_of(fl.get("turkish", ""), fl["fix"], fl["quote"])
        fixw = set(pw(fl["fix"]))
        wrong = ([c for c in inside if c["prep"].split()[-1] not in fixw] or inside)[:1]   # one slip per flag: the preposition that changed
        if inside:
            for c in wrong: c.update(ok=False, right=right, flag=fl["quote"], fix=fl["fix"], group=grp)
        else:
            extra.append({"turn": tid, "mode": C.get("modes", {}).get(tid) or fl.get("mode") or "voice", "lemma": k, "prep": "∅", "obj": "", "ok": False,
                          "right": right, "flag": fl["quote"], "fix": fl["fix"], "group": grp, "dropped": True})
        if k and k not in watch:   # a first slip puts the word in the waiting area; a second puts it on the list (Murat, 16.10.26)
            watch[k] = {"word": k, "right": right, "group": grp, "slips": 0, "examples": [], "status": "waiting", "new": True}
        if k:
            r = watch[k]; r["slips"] += 1; r["changed"] = True
            r["examples"] = ([{"date": fl.get("date", ""), "said": fl["quote"][:120], "fix": fl["fix"][:120], **({"doc": fl["doc"]} if fl.get("doc") else {})}] + r.get("examples", []))[:6]
            if r.get("status", "on") == "waiting" and r["slips"] >= 2: r["status"] = "on"; r["promoted"] = True
    # right "no preposition" uses: every use of a ZERO verb on the watch list that has no preposition after it
    on = {w for w, r in watch.items() if r.get("status", "on") == "on"}   # only words on the list are tracked one by one
    zero_watch = {w for w in on if watch[w].get("right") == "∅" and w in ZERO}
    seen_heads = {(c["turn"], c.get("hidx")) for c in cands}
    flagged_turn_words = {(u["turn"], u.get("lemma")) for u in extra}
    for tid, text in turns.items():
        for t in nlp(text):
            L = t.lemma_.lower()
            if L in zero_watch and t.pos_ == "VERB" and (tid, t.i) not in seen_heads and (tid, L) not in flagged_turn_words:
                extra.append({"turn": tid, "mode": C.get("modes", {}).get(tid, "voice"), "lemma": L, "prep": "∅", "obj": "", "ok": True, "right": "∅"})
    uses = cands + extra   # voice and typed both count (Murat, 16.10.26); every figure also comes split by mode
    # raw counts [right, uses] per mode, so the Ledger can add sessions together; "all" = voice + typed
    def acc(xs): return {m: [sum(1 for x in xs if x.get("mode") == m and x["ok"]), sum(1 for x in xs if x.get("mode") == m)] for m in ("voice", "typed")}
    order = {t: i for i, t in enumerate(turns)}
    wl = sorted([u for u in uses if u.get("lemma") in on], key=lambda u: (order.get(u["turn"], 0), u.get("start", 0)))
    for u in wl: u.setdefault("group", watch[u["lemma"]]["group"])
    by_g = collections.defaultdict(list); by_w = collections.defaultdict(list); by_c = collections.defaultdict(list)
    for u in wl: by_g[u["group"]].append(u); by_w[u["lemma"]].append(u)
    for u in uses:
        need = u["prep"] if u["ok"] else u.get("right", "∅")
        by_c["∅ no preposition" if need == "∅" else chip_of(need, u.get("obj"))].append(u)
    # seq: every use of the word in order; R/W = voice right/wrong, r/w = typed right/wrong
    seq = lambda xs: "".join(("R" if x["ok"] else "W") if x.get("mode") == "voice" else ("r" if x["ok"] else "w") for x in xs)
    out = {"v": 1, "all": acc(uses), "watch": acc(wl),
           "groups": {g: acc(v) for g, v in by_g.items()},
           "chips": {c: acc(v) for c, v in by_c.items()},
           "words": {w: {**acc(v), "seq": seq(v)} for w, v in by_w.items()},
           "wrong": [{k: u.get(k) for k in ("turn", "mode", "lemma", "prep", "right", "flag", "fix", "group", "dropped")} for u in uses if not u["ok"]],
           "unmatched_flags": [f["quote"] for f in flags if f.get("unmatched")],
           "new_waiting": sorted(w for w, r in watch.items() if r.get("new") and r["status"] == "waiting"),
           "joined_list": sorted(w for w, r in watch.items() if r.get("promoted")),
           "watch_changes": [{k: v for k, v in r.items() if k not in ("changed", "new", "promoted")} for r in watch.values() if r.get("changed")]}
    pc = lambda c: f'{round((c["voice"][0] + c["typed"][0]) / max(1, c["voice"][1] + c["typed"][1]) * 100)}% of {c["voice"][1] + c["typed"][1]}'
    json.dump(out, open(out_path, "w"), ensure_ascii=False, indent=1)
    print("all", pc(out["all"]), "voice", out["all"]["voice"], "typed", out["all"]["typed"], "| watch list", pc(out["watch"]), "| wrong", len(out["wrong"]), "| joined the list", out["joined_list"], "| waiting", len(out["new_waiting"]))

# ---- the naturalness check's step (16.10.26): one command, fails softly, writes nothing unless it finishes
def flags_of(doc):
    """The check's own preposition slips in the session doc: interference preposition_case + err_preposition (same slip once)."""
    norm = lambda x: re.sub(r"[^a-z ]", "", (x or "").lower())
    fl = [dict(quote=i["quote"], fix=i.get("fix", ""), turkish=i.get("turkish", ""), mode=i.get("mode"), turn=i.get("turn"))
          for i in (doc.get("interference") or {}).get("items", []) if i.get("type") == "preposition_case" and i.get("counted", True) is not False]
    seen = [norm(i["quote"]) for i in fl]
    for e in doc.get("errors", []):
        if e.get("concept") != "err_preposition": continue
        q = norm(e.get("quote"))
        if any(x and (x in q or q in x) for x in seen): continue
        fl.append(dict(quote=e.get("quote", ""), fix=(e.get("fix") or "").split("->")[-1].strip(), turkish="", mode=e.get("mode")))
    return fl

def cmd_run(turns_path, doc_path, watch_path, watch_out, doc_id):
    import tempfile, datetime
    try:
        doc = json.load(open(doc_path)); W = json.load(open(watch_path)); W = W.get("data", W) if "rows" not in W else W
        log = W.setdefault("log", {})
        rows = {r["word"]: r for r in W["rows"]}
        # a second run in the same chat first takes back what the first run added
        for w, n in log.pop(doc_id, {}).items():
            r = rows.get(w)
            if not r: continue
            r["slips"] -= n; r["examples"] = [e for e in r.get("examples", []) if e.get("doc") != doc_id]
            if r["slips"] <= 0 and r.get("added") == doc_id: del rows[w]
        for r in rows.values(): r["status"] = "on" if r["slips"] >= 2 else "waiting"
        before = {w: r["slips"] for w, r in rows.items()}
        fl = flags_of(doc)
        for f in fl: f["date"] = doc.get("date", ""); f["doc"] = doc_id
        tmp = tempfile.mkdtemp(prefix="preps_")
        P = lambda n: os.path.join(tmp, n)
        json.dump(list(rows.values()), open(P("watch.json"), "w"), ensure_ascii=False)
        json.dump(fl, open(P("flags.json"), "w"), ensure_ascii=False)
        cmd_find(turns_path, P("cands.json"))
        cmd_score(P("cands.json"), P("flags.json"), P("watch.json"), P("out.json"))
        o = json.load(open(P("out.json")))
        for r in o["watch_changes"]:
            if r["word"] not in rows: r["added"] = doc_id
            rows[r["word"]] = r
        added = {w: r["slips"] - before.get(w, 0) for w, r in rows.items() if r["slips"] - before.get(w, 0) > 0}
        if added: log[doc_id] = added
        for r in rows.values(): r["status"] = "on" if r["slips"] >= 2 else "waiting"
        W["rows"] = sorted(rows.values(), key=lambda r: -r["slips"]); W["as_of"] = datetime.date.today().isoformat()
        doc["preps"] = {k: o[k] for k in ("v", "all", "watch", "groups", "chips", "words", "wrong", "unmatched_flags")}
        doc["preps"]["joined_list"] = o["joined_list"]; doc["preps"]["new_waiting"] = o["new_waiting"]
        t = doc_path + ".tmp"; json.dump(doc, open(t, "w"), ensure_ascii=False, indent=1); os.replace(t, doc_path)
        json.dump(W, open(watch_out, "w"), ensure_ascii=False, indent=1)
    except Exception as e:   # fail softly: the check goes on without preposition figures
        if os.path.exists(watch_out): os.remove(watch_out)
        print(f"PREPS SKIPPED: {type(e).__name__}: {e}. session_doc.json was not changed; leave meta/prep_watch out of the save and say so in the report.")
        return
    pc = lambda c: (f'{round(c[0] / c[1] * 100)}% of {c[1]}' if c[1] else "no uses")
    tot = lambda c: [c["voice"][0] + c["typed"][0], c["voice"][1] + c["typed"][1]]
    gs = sorted(((g, tot(c)) for g, c in o["groups"].items() if g != "other" and tot(c)[1] >= 10), key=lambda x: x[1][0] / x[1][1])
    print(f'PREPS: all {pc(tot(o["all"]))} (voice {pc(o["all"]["voice"])}, typed {pc(o["all"]["typed"])})')
    print(f'PREPS: watch list {pc(tot(o["watch"]))} (voice {pc(o["watch"]["voice"])}, typed {pc(o["watch"]["typed"])})')
    if gs: print(f'PREPS: weakest group {gs[0][0]} {pc(gs[0][1])}')
    print(f'PREPS: slips {len(o["wrong"])}; joined the list: {", ".join(o["joined_list"]) or "none"}; new, waiting: {", ".join(o["new_waiting"]) or "none"}')
    if o["unmatched_flags"]: print(f'PREPS: {len(o["unmatched_flags"])} slip(s) not found in the turns, counted as wrong anyway')
    print("PREPS: wrote the preps block into session_doc.json and", watch_out)

if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    {"find": cmd_find, "seed": cmd_seed, "score": cmd_score, "run": cmd_run}[cmd](*a)
