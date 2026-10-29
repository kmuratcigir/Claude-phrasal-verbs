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

FILLERS = re.compile(r"\b(?:uh|um|erm|er|hmm)\b,?|\bsorry\b,?(?!\s+(?:for|about|if|that|to)\b)", re.I)

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

# ---------- shared helpers for the finders below ----------
SUBJ = r"(?:i|you|we|they|he|she|it|this|that|there|people|everyone|nobody|someone)"
IRREG_PAST = "went|came|saw|did|got|made|took|gave|told|said|found|heard|sent|left|met|began|ran|wrote|read|bought|thought|brought|caught|taught|won|lost|built|spent|put|set|cut|let|knew|felt|kept|held|stood|understood|forgot|became|chose|drove|ate|drank|spoke|broke|woke|sat|fell|grew|threw|flew|paid|sold|slept|meant|left|lent|led|fed|hung|hit|hurt|shut|quit|rose"
IRREG_PP = "gone|come|seen|done|got|gotten|made|taken|given|told|said|found|heard|sent|left|met|begun|run|written|read|bought|thought|brought|caught|taught|won|lost|built|spent|put|set|cut|let|known|felt|kept|held|stood|understood|forgotten|become|chosen|driven|eaten|drunk|spoken|broken|woken|sat|fallen|grown|thrown|flown|paid|sold|slept|meant|been|had"
PAST_W = rf"(?:\w+ed|{IRREG_PAST})"
PP_W = rf"(?:\w+ed|{IRREG_PP})"
HAVE = r"(?:have|has|had|'ve|’ve|'s|’s|haven't|hasn't|haven’t|hasn’t)"

def prev_words(sent, pos, n=2):
    return [w.lower().strip(",.") for w in sent[:pos].split()[-n:]]

NOUN_PRE = {"an", "the", "my", "our", "your", "his", "her", "their", "this", "new", "different", "good", "right", "wrong", "same", "that", "whole"}
CONTACT_PRE = {"in", "the", "a", "my", "our", "your", "his", "her", "their", "this", "that", "of", "main", "first"}

def clauses(sent):
    return [c.strip() for c in re.split(r"[,;:]|\b(?:but|and|so|because|although|while)\b", sent, flags=re.I) if c.strip()]

# ---------- chunk 2: verbs with a fixed preposition, or none (closed list of 10) ----------
DET = r"(?:me|us|you|him|her|them|it|this|that|these|those|the|a|an|my|our|your|his|their|its|some|any|all|every|each|people|everyone|\d+|(?-i:[A-Z])\w+)"
C2_RULES = [
    # (name, regex, suggestion)  suggestion True = correct, False = wrong
    ("approach", re.compile(rf"\bapproach(?:es|ed|ing)?\s+to\b(?!\s+(?:the\s+)?(?:problem|issue|question|learning|it\b))", re.I), False),
    ("approach", re.compile(rf"\bapproach(?:es|ed|ing)?\s+{DET}\b", re.I), True),
    ("mention", re.compile(r"\bmention(?:s|ed|ing)?\s+about\b", re.I), False),
    ("mention", re.compile(rf"\bmention(?:s|ed|ing)?\s+(?!about\b|before\b|earlier\b|above\b|previously\b|again\b|already\b)(?:it|that|this|these|the|a|an|my|our|your|his|her|their|some|any|him|them|(?-i:[A-Z])\w+)\b", re.I), True),
    ("research", re.compile(rf"\b(?:to|will|can|could|should|would|did|didn['’]t|{SUBJ})\s+research(?:ed)?\s+about\b|\bresearch(?:ed|ing)\s+about\b", re.I), False),
    ("research", re.compile(rf"\b(?:to|will|can|could|should|would|did|didn['’]t|{SUBJ})\s+research(?:ed)?\s+(?!about\b|on\b|into\b|is\b|was\b|shows\b){DET}\b|\bresearch(?:ed|ing)\s+(?!about\b|on\b|into\b){DET}\b", re.I), True),
    ("contact", re.compile(r"\bcontact(?:s|ed|ing)?\s+(?:with|to)\b", re.I), False),
    ("contact", re.compile(rf"\bcontact(?:s|ed|ing)?\s+(?!with\b|to\b|person\b|details\b|list\b|form\b|number\b){DET}\b", re.I), True),
    ("join", re.compile(r"\bjoin(?:s|ed|ing)?\s+(?:to|with)\b", re.I), False),
    ("join", re.compile(rf"\bjoin(?:s|ed|ing)?\s+(?!in\b|to\b|with\b|up\b|forces\b){DET}\b", re.I), True),
    ("discuss", re.compile(r"\bdiscuss(?:es|ed|ing)?\s+about\b", re.I), False),
    ("discuss", re.compile(rf"\bdiscuss(?:es|ed|ing)?\s+(?!about\b){DET}\b", re.I), True),
    ("remind of", re.compile(rf"\bremind(?:s|ed|ing)?\s+{DET}(?:\s+\w+)?\s+(?:of|about)\b", re.I), True),
    ("remind of", re.compile(r"\bremind(?:s|ed|ing)?\s+(?:me|us|you|him|her|them)\s+(?!of\b|about\b|to\b|that\b|how\b|what\b|when\b|why\b|where\b|who\b|if\b|again\b|later\b|tomorrow\b)(?:the|a|an|my|your|his|her|our|their|this|that|these|some|\w+ing)\b", re.I), False),
    ("responsible for", re.compile(r"\bresponsible\s+for\b", re.I), True),
    ("responsible for", re.compile(r"\bresponsible\s+(?:from|of|about|on)\b", re.I), False),
    ("bored with", re.compile(r"\bbored\s+(?:with|of)\b", re.I), True),
    ("bored with", re.compile(r"\bbored\s+(?:from|about|to|on)\b", re.I), False),
    ("knowledge of", re.compile(r"\bknowledge\s+of\b", re.I), True),
    ("knowledge of", re.compile(r"\bknowledge\s+for\b", re.I), False),
    ("knowledge of", re.compile(r"\bknowledge\s+(?:about|on)\b", re.I), None),
]

def find_c2(sent):
    out, spans = [], []
    for name, rx, ok in C2_RULES:
        for m in rx.finditer(sent):
            if any(m.start() < e and s < m.end() for s, e in spans): continue
            pw = prev_words(sent, m.start(), 1)
            if name == "approach" and pw and pw[-1] in NOUN_PRE: continue
            if name == "contact" and pw and pw[-1] in CONTACT_PRE: continue
            spans.append((m.start(), m.end()))
            out.append({"item": "c2", "match": m.group(0).strip(), "word": name, "suggest": ok})
    return out

# ---------- chunk 3: "to", not "for + -ing", for purpose (rough) ----------
NOT_PURPOSE_BEFORE = r"(?:used|useful|good|bad|great|perfect|ideal|thanks?|thank\s+you|sorry|apologi\w+|responsible|known|famous|excuse|reason|time|way|chance|opportunity|tool|tools|machine|app|place|room|space|plan|ready|blame\w*|forgive\w*|punish\w*|arrest\w*|instead|pay|paid|criticis\w+|look|looking|interested|passion|need|room|motivation|eager\w*|struggle\w*|struggling|appetite|habit|skill|talent|tendency)"
C3_WRONG = re.compile(r"\bfor\s+(?:\w+ly\s+)?(\w+ing)\b", re.I)
NOT_PURPOSE_RX = re.compile(rf"^{NOT_PURPOSE_BEFORE}$", re.I)
C3_RIGHT = [
    re.compile(r"\bin order to\s+\w+", re.I),
    re.compile(r"^\s*to\s+(?!be\s+honest|me\b|you\b|him\b|her\b|us\b|them\b|the\b|a\b|my\b|your\b|be\s+fair)[a-z]+\b[^,]{0,60},", re.I),
    re.compile(r"\b(?:use|used|uses|using)\s+(?:[\w'’]+\s+){1,4}to\s+(?!the\b|a\b|my\b|me\b|you\b|him\b|her\b|us\b|them\b|this\b|that\b)[a-z]+\b", re.I),
    re.compile(r"(?<!it\s)\b(?:came|come|comes|went|go|goes|going|called|call|calls|stayed|stay|here|there)\s+(?!to\s+(?:surface|mind|terms|an end|light|life)\b)(?:[\w'’]+\s+){0,3}to\s+(?!the\b|a\b|my\b|me\b|you\b|him\b|her\b|us\b|them\b|this\b|that\b|bed\b|work\b|school\b|London\b|office\b)[a-z]+\b", re.I),
]
ING_NOT_VERB = {"something", "anything", "nothing", "everything", "morning", "evening", "thing", "things", "during", "spring", "king", "ring", "string", "ceiling", "building", "meeting", "wedding", "training", "feeling", "beginning", "living", "being"}

def find_c3(sent):
    out = []
    for m in C3_WRONG.finditer(sent):
        if any(NOT_PURPOSE_RX.match(w) for w in prev_words(sent, m.start(), 2)): continue
        if m.group(1).lower() in ING_NOT_VERB and m.group(1).lower() not in ("being", "living"): continue
        use_before = re.search(r"\b(?:use|used|uses|using)\b(?:\s+[\w'’]+){0,6}\s*$", sent[:m.start()], re.I)
        out.append({"item": "c3", "match": m.group(0).strip(), "suggest": None if use_before else False})
    for rx in C3_RIGHT:
        for m in rx.finditer(sent):
            out.append({"item": "c3", "match": m.group(0).strip()[:60], "suggest": True})
            break
    return out

# ---------- chunk 4: no "a" before uncountable nouns (closed list) ----------
UNC = "feedback|news|advice|information|homework|equipment|evidence|progress|luggage|furniture|research"
UNC_PL = "feedbacks|advices|informations|homeworks|equipments|evidences|luggages|furnitures"
NOUN_AFTER = r"(?:session|sessions|loop|form|forms|tool|meeting|report|system|channel|call|item|items|request|page|link|programme|program|team|desk|centre|center|agency|anchor|article|articles|bulletin|app|site|website|paper|papers|project|projects|grant|question|questions|study|lab|group|assistant|scientist|scientists|method|methods|area|field|topic|bar|bag|bags|allowance|rack|store|shop|policy|check|update|reel|story|stories|outlet|feed)"
C4_A = re.compile(rf"\b(a|an)\s+((?:(?!of\b|lot\b|bit\b|piece\b|kind\b|sort\b|type\b|lack\b)[\w'’-]+\s+){{0,2}})({UNC})\b(?!\s+{NOUN_AFTER}\b)", re.I)
C4_PL = re.compile(rf"\b({UNC_PL})\b", re.I)
C4_ANY = re.compile(rf"\b({UNC})\b(?!\s+{NOUN_AFTER}\b)", re.I)
RESEARCH_VERB = re.compile(rf"\b(?:to|will|can|could|should|would|did|didn['’]t|{SUBJ})\s+research\b", re.I)

def find_c4(sent):
    out, spans = [], []
    for m in C4_A.finditer(sent):
        spans.append(m.span(3)); out.append({"item": "c4", "match": m.group(0).strip(), "suggest": False})
    for m in C4_PL.finditer(sent):
        spans.append(m.span(1)); out.append({"item": "c4", "match": m.group(0), "suggest": False})
    for m in C4_ANY.finditer(sent):
        if any(s <= m.start() < e for s, e in spans): continue
        if m.group(1).lower() == "research" and RESEARCH_VERB.search(sent[max(0, m.start()-25):m.end()]): continue
        out.append({"item": "c4", "match": sent[max(0, m.start()-12):m.end()].strip(), "suggest": True})
    return out

# ---------- chunk 5: "still" goes before "have" ----------
C5_WRONG = re.compile(r"\b(?:have|has|had)\s+still\s+(?!not\b|got\b|been\b|\w+ed\b|gone\b|done\b|seen\b|made\b)(?:[\w'’]+)", re.I)
C5_WRONG2 = re.compile(r"\b(?:haven['’]t|hasn['’]t|hadn['’]t)\s+still\b", re.I)
C5_RIGHT = re.compile(r"\bstill\s+(?:have|has|had|haven['’]t|hasn['’]t|hadn['’]t)\b|\b(?:['’]ve|have|has|['’]s)\s+still\s+got\b", re.I)

def find_c5(sent):
    out = []
    for rx, ok in ((C5_WRONG, False), (C5_WRONG2, False), (C5_RIGHT, True)):
        for m in rx.finditer(sent):
            out.append({"item": "c5", "match": m.group(0).strip(), "suggest": ok})
    return out

# ---------- slice 2: "already" / "just" -> present perfect ----------
HAVE_PRES = r"(?:have|has|'ve|’ve|'s|’s|haven't|hasn't|haven’t|hasn’t)"
S2_RIGHT = re.compile(rf"\b{HAVE_PRES}\s+(?:already|just)\s+{PP_W}\b|\b{HAVE_PRES}\s+{PP_W}\s+(?:[\w'’]+\s+){{0,4}}already\b", re.I)
S2_WRONG_ALREADY = re.compile(rf"\balready\s+({PAST_W}|{IRREG_PP})\b|\b{SUBJ}\s+({PAST_W})\s+(?:[\w'’]+\s+){{0,4}}already\b", re.I)
JUST_EVENT = "finished|arrived|left|came|got|saw|heard|sent|told|started|began|ended|landed|called|said|found|met|woke|returned|joined|bought|read|published|launched|signed|received|done|seen"
S2_WRONG_JUST = re.compile(rf"\b{SUBJ}\s+just\s+({JUST_EVENT})\b", re.I)
S2_FIXED = re.compile(r"\bas\s+(?:you|i|we|he|she|they)\s+just\s+(?:said|mentioned|told|did|saw|heard)\b", re.I)

def find_s2(sent):
    out, spans = [], []
    for m in S2_RIGHT.finditer(sent):
        spans.append(m.span()); out.append({"item": "s2", "match": m.group(0).strip(), "suggest": True})
    for rx in (S2_WRONG_ALREADY, S2_WRONG_JUST):
        for m in rx.finditer(sent):
            if any(s <= m.start() < e for s, e in spans): continue
            if re.search(rf"\b(?:have|has|had|'ve|'s|'d|’ve|’s|’d)\b", sent[max(0, m.start()-12):m.start()], re.I): continue
            if any(f.start() <= m.start() < f.end() + 2 for f in S2_FIXED.finditer(sent)): continue
            out.append({"item": "s2", "match": m.group(0).strip(), "suggest": False})
    return out

# ---------- slice 3: finished time -> past simple ----------
FIN = re.compile(r"\byesterday\b|\b\w+\s+ago\b|(?<!\bthe\s)(?<!\bsince\s)(?<!\bfor\s)(?<!\bin\s)\blast\s+(?:week|month|year|night|time|weekend|summer|winter|spring|autumn|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b|(?<!\bsince\s)\bin\s+(?:19|20)\d\d\b|\bwhen i was\b", re.I)
S3_PERFECT = re.compile(rf"\b{HAVE}\s+(?:not\s+|never\s+|already\s+|just\s+|also\s+)?(?:been\s+)?{PP_W}\b", re.I)
S3_PAST = re.compile(rf"\b(?:was|were|did|didn['’]t|{PAST_W})\b", re.I)

def find_s3(sent):
    out = []
    for c in clauses(sent):
        if not FIN.search(c) or re.search(r"\b(?:since|for the last|the last few|in the last|so far|this (?:week|month|year))\b", c, re.I): continue
        if S3_PERFECT.search(c): out.append({"item": "s3", "match": c[:80], "suggest": False})
        elif S3_PAST.search(c): out.append({"item": "s3", "match": c[:80], "suggest": True})
    return out

# ---------- slice 4: "for" / "since" for things still going on ----------
DUR = re.compile(r"\bfor\s+(?:about\s+|almost\s+|nearly\s+|over\s+|more than\s+)?(?:\d+|a|an|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|many|several|a few|a couple of)\s+(?:years?|months?|weeks?|days?|hours?|decades?)\b|\bfor\s+(?:ages|a long time|a while)\b", re.I)
SINCE_T = re.compile(r"\bsince\s+(?:\d{4}\b|last\b|(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|january|february|march|april|may|june|july|august|september|october|november|december)\b|then\b|childhood\b|the (?:start|beginning)\b|(?:i|we|he|she|they)\s+(?:was|were)\b|\d)", re.I)
S4_PERF = re.compile(rf"\b{HAVE}\s+(?:not\s+|never\s+|been\s+\w+ing|{PP_W})", re.I)
S4_PRES = re.compile(rf"\b(?:am|is|are|['’]m|['’]re)\s+\w+ing\b|\b(?:i|we|they|you)\s+(?:know|live|work|have|study|teach|use|play|own)\b|\b(?:he|she|it)\s+(?:knows|lives|works|has|studies|teaches|uses|plays|owns)\b", re.I)
S4_FUT = re.compile(r"\b(?:will|going to|next|tomorrow|plan to|planning)\b", re.I)

def find_s4(sent):
    out = []
    for c in clauses(sent):
        d, s = DUR.search(c), SINCE_T.search(c)
        if not (d or s): continue
        if S4_FUT.search(c): continue
        if S4_PERF.search(c): out.append({"item": "s4", "match": c[:80], "suggest": True})
        elif S4_PRES.search(c):
            cont = re.search(r"\b(?:am|is|are|['’]m|['’]re)\s+\w+ing\b", c, re.I)
            long_ = re.search(r"\b(?:years?|months?|decades?|ages|a long time)\b", c, re.I)
            out.append({"item": "s4", "match": c[:80], "suggest": False if (s or not cont or long_) else None})
        elif s: out.append({"item": "s4", "match": c[:80], "suggest": None})
    return out

# ---------- shared for s5-s7 (added 29.10.26) ----------
def clauses_keep(sent):
    """Like clauses(), but "so far" is never split at its "so"."""
    s = re.sub(r"\bso\s+far\b", "so_far", sent, flags=re.I)
    parts, out = [c.replace("so_far", "so far") for c in clauses(s)], []
    for c in parts:   # a fronted phrase on its own ("Up to now, ...", "Lately, ...") joins the next clause
        if out and len(out[-1].split()) <= 3: out[-1] = out[-1] + ", " + c
        else: out.append(c)
    return out

PERF_PRES = re.compile(rf"\b{HAVE_PRES}\s+(?:(?:i|you|we|they|he|she|it|anyone|everyone|anybody)\s+)?(?:not\s+|ever\s+|never\s+|really\s+|just\s+|already\s+|also\s+|only\s+)*(?:been|{PP_W})\b", re.I)
PAST_ANY = re.compile(rf"\b(?:had|was|were|did|didn['’]t|did\s+not|wasn['’]t|weren['’]t|{PAST_W})\b", re.I)
FUTURE = re.compile(r"\b(?:will|won['’]t|['’]ll|going to|gonna|plan(?:ning)? to|next|tomorrow)\b", re.I)
FINISHED = re.compile(r"\byesterday\b|\b\w+\s+ago\b|\blast\s+\w+|\bin\s+(?:19|20)\d\d\b|\bwhen\s+(?:i|we|he|she|they)\s+(?:was|were)\b|\bas\s+a\s+(?:child|kid|student)\b|\bafter\s+(?:that|\d{4}|school|university)\b|\buntil\s+then\b|\bat\s+(?:that|the)\s+time\b|\bback\s+then\b|\bon\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)

# ---------- slice 5: "ever / never" for life experience -> present perfect ----------
S5_SKIP = re.compile(r"\bever\s+since\b|\bforever\b|\bhardly\s+ever\b|\b(?:best|worst|biggest|first|only|most|least|greatest|hardest)\b[\w\s'’]{0,25}\bever\b|\bthan\s+ever\b|\bnever\s+mind\b|\bnever\s+again\b|\bnow\s+or\s+never\b|\b(?:would|could|can|should|might|must|had|'d|’d)\s+(?:\w+\s+)?never\b|\bnever\s+(?:ever\s+)?(?:be|have|do|let|give)\b(?!\s+(?:been|had|done))", re.I)
S5_PAST_NEVER = re.compile(rf"\b(?:never|ever)\s+(?:{PAST_W})\b|\b(?:did|didn['’]t)\s+(?:\w+\s+){{0,2}}ever\b|\b(?:was|were)\s+never\b", re.I)

def find_s5(sent):
    out = []
    for c in clauses_keep(sent):
        if not re.search(r"\b(?:ever|never)\b", c, re.I): continue
        if S5_SKIP.search(c) or FUTURE.search(c) or FINISHED.search(c): continue
        if PERF_PRES.search(c): out.append({"item": "s5", "match": c[:80], "suggest": True})
        elif S5_PAST_NEVER.search(c): out.append({"item": "s5", "match": c[:80], "suggest": None})   # life experience or a finished time? Claude decides
    return out

# ---------- slice 6: "so far / up to now / until now" -> present perfect ----------
S6_PHRASE = re.compile(r"\bso\s+far\b|\b(?:up\s+)?(?:to|until|till)\s+now\b|\bto\s+date\b", re.I)
S6_SKIP = re.compile(r"\bso\s+far\s+(?:from|away)\b|\bnot\s+so\s+far\b|\bso\s+far,?\s+so\s+good\b|\bas\s+far\s+as\b|\b(?:until|till)\s+now\b.*\b(?:know|knew|realis|realiz|think|thought|understood|notic)|\b(?:know|knew|realis|realiz|think|thought|understood|notic)\w*\b.*\b(?:until|till)\s+now\b", re.I)

def find_s6(sent):
    out = []
    for c in clauses_keep(sent):
        if not S6_PHRASE.search(c) or S6_SKIP.search(c) or FUTURE.search(c): continue
        if PERF_PRES.search(c): out.append({"item": "s6", "match": c[:80], "suggest": True})
        elif PAST_ANY.search(c): out.append({"item": "s6", "match": c[:80], "suggest": False})
    return out

# ---------- slice 7: "this week / month / year", "lately" -> present perfect ----------
S7_PHRASE = re.compile(r"\bthis\s+(?:week|month|year)\b(?!['’]s)|\blately\b", re.I)
S7_SPECIFIC = re.compile(r"\bon\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b|\byesterday\b|\bthis\s+morning\b|\btoday\b|\bat\s+\d|\bin\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\b", re.I)
S7_PRES = re.compile(r"\b(?:am|is|are|['’]m|['’]re)\b", re.I)

def find_s7(sent):
    out = []
    for c in clauses_keep(sent):
        m = S7_PHRASE.search(c)
        if not m or FUTURE.search(c) or S7_SPECIFIC.search(c): continue
        lately = m.group(0).lower() == "lately"
        if PERF_PRES.search(c): out.append({"item": "s7", "match": c[:80], "suggest": True})
        elif PAST_ANY.search(c): out.append({"item": "s7", "match": c[:80], "suggest": False if lately else None})
        elif lately and S7_PRES.search(c): out.append({"item": "s7", "match": c[:80], "suggest": None})
    return out

FINDERS = {"c1": find_c1, "c2": find_c2, "c3": find_c3, "c4": find_c4, "c5": find_c5,
           "s1": find_s1, "s2": find_s2, "s3": find_s3, "s4": find_s4,
           "s5": find_s5, "s6": find_s6, "s7": find_s7}

def slot_turns(path):
    """Turns tagged [slot] in the header: inside the fixing slot marks (29.10.26)."""
    out = set()
    for line in open(path, encoding="utf-8"):
        m = re.match(r"###\s*(T\d+)\b(.*)$", line)
        if m and "[slot]" in m.group(2): out.add(m.group(1))
    return out

def cmd_find(turns_path, chunks_path, out_path, targets_path=None):
    """targets_path (optional, 29.10.26): the fixing slot's drilled chunk ids, one per line
    (from the slot's "Drilled targets:" line). Their uses inside the slot marks are practice:
    kept out of the candidates and printed as a SLOT LIST for the slot result only."""
    import os
    if not os.path.exists(chunks_path):
        json.dump({"open": [], "candidates": []}, open(out_path, "w"))
        print("No meta/chunks in the ledger: chunk counting skipped."); return
    meta = json.load(open(chunks_path, encoding="utf-8"))
    meta = meta.get("data", meta)
    open_ids = [it["id"] for it in meta["items"] if it["status"] == "open"]
    missing = [i for i in open_ids if i not in FINDERS]
    if missing:
        print("NOT COUNTED (no finder yet, say so in the report):", ", ".join(missing))
        open_ids = [i for i in open_ids if i in FINDERS]
    targets = set()
    if targets_path and os.path.exists(targets_path):
        targets = {l.strip() for l in open(targets_path, encoding="utf-8") if l.strip()}
    in_slot = slot_turns(turns_path)
    cands, slot = [], []
    for t in read_turns(turns_path):
        for raw in sentences(t["text"]):
            s = clean(raw)
            for iid in open_ids:
                for c in FINDERS[iid](s):
                    c.update(turn=t["turn"], mode=t["mode"], sentence=s)
                    (slot if (iid in targets and t["turn"] in in_slot) else cands).append(c)
    for i, c in enumerate(cands): c["idx"] = i
    json.dump({"open": open_ids, "candidates": cands}, open(out_path, "w"), ensure_ascii=False, indent=1)
    print(f"CHUNK REVIEW LIST · open: {', '.join(open_ids)} · {len(cands)} candidates")
    for c in cands:
        sug = {True: "correct", False: "WRONG", None: "decide"}[c["suggest"]]
        print(f'{c["idx"]:3} {c["item"]} {c["mode"]:5} {c["turn"]:5} {sug:7} | {c["match"]} | {c["sentence"][:110]}')
    if slot:
        print(f"SLOT LIST (kept out of the chunk counts: drilled targets inside the fixing slot) · {len(slot)}")
        for c in slot:
            sug = {True: "correct", False: "WRONG", None: "decide"}[c["suggest"]]
            print(f'  - {c["item"]} {c["mode"]:5} {c["turn"]:5} {sug:7} | {c["match"]} | {c["sentence"][:110]}')
    elif targets and not in_slot:
        print("SLOT: targets given but no turn is tagged [slot]; check the marks before going on.")

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
