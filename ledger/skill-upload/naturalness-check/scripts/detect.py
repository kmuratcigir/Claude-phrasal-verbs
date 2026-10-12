#!/usr/bin/env python3
"""
Exhaustive grammar/cohesion candidate detector for Murat's speech.

Why this exists: asking an LLM to "read the transcript and notice patterns"
produced a handful of hand-picked highlights (5 items from a whole session).
This script instead parses EVERY sentence with spaCy and flags every
syntactic match mechanically. Claude's job afterwards is only to confirm
each flagged candidate (correct / error / false positive), not to find them.

Input : a text file of Murat's own turns, separated by lines "### T<n> [voice]" or
        "### T<n> [typed]" (voice = transcribed speech, typed = written in the chat)
Output: JSON list of candidates {turn, concept, level, kind, sentence, match}
Usage : python3 detect.py murat_turns.txt candidates.json
"""
import re, sys, json
import spacy

nlp = spacy.load("en_core_web_sm")

# ---------------------------------------------------------------- cleaning
# fillers are cut from every count and every quote (Murat, 29.09.26): uh, uhm, um, mmm, hmm, er, erm, eh, ah...
FILLER = re.compile(r"\b(u+h+m*|u+m+|m{2,}|h+m+|e+r+m*|e+h+m*|a+h+)\b[,.]?\s*", re.I)
REPEAT = re.compile(r"\b(\w+)(?:,?\s+\1\b)+", re.I)   # "the, the, the" -> "the"

SOFT = re.compile(r"\b(you know|i mean)\b,?\s*", re.I)
def clean(text):
    t = FILLER.sub("", text)
    t = SOFT.sub("", t)
    t = REPEAT.sub(r"\1", t)
    t = re.sub(r"\s+([,.?!])", r"\1", t)
    t = re.sub(r"([,.])\s*[,.]+", r"\1", t)
    return re.sub(r"\s{2,}", " ", t).strip()

def load_turns(path):
    """-> [(turn, text, mode)], mode 'voice' or 'typed' (untagged turns count as typed)."""
    turns, cur, mode, buf = [], None, "typed", []
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^### (T\d+)(?:\s*\[(voice|typed)\])?", line)
        if m:
            if cur: turns.append((cur, " ".join(buf), mode))
            cur, mode, buf = m.group(1), (m.group(2) or "typed"), []
        else:
            buf.append(line.strip())
    if cur: turns.append((cur, " ".join(buf), mode))
    return turns

# ---------------------------------------------------------------- helpers
def lem(t): return t.lemma_.lower()
def low(t): return t.text.lower()
HAVE_FORMS = {"have", "has", "'ve", "'s", "ve"}

def aux_children(v):
    return [c for c in v.children if c.dep_ in ("aux", "auxpass")]

# --------------------------------------------------------------- detectors
# Each detector takes a sentence Span and yields (concept, level, kind, match)
# kind: "use" = candidate usage of a concept, "error" = likely error signature
def d_tenses(s):
    for v in s:
        if v.pos_ not in ("VERB", "AUX"): continue
        auxs = aux_children(v)
        a = [low(x) for x in auxs]
        if v.tag_ == "VBN" and any(x in HAVE_FORMS for x in a) and "had" not in a \
           and not any(x.tag_ == "MD" for x in auxs):
            # "'s" could be "is": require a real have-form or 's + been
            if not ("'s" in a and not any(low(x) == "been" for x in auxs)) or v.text.lower() == "been":
                yield ("b1_present_perfect", "B1", "use", v.text)
        if v.tag_ == "VBN" and "had" in a:
            yield ("b2_past_perfect", "B2", "use", v.text)
        if v.tag_ == "VBG" and "been" in a and any(x in HAVE_FORMS for x in a):
            yield ("b2_present_perfect_continuous", "B2", "use", v.text)
        if v.tag_ == "VBG" and any(x in ("was", "were") for x in a) and v.dep_ not in ("acomp", "amod"):
            yield ("b1_past_continuous", "B1", "use", v.text)
        if v.tag_ == "VBG" and any(x in ("am", "is", "are", "'m", "'re") for x in a) \
           and low(v) != "going":
            yield ("a2_present_continuous", "A2", "use", v.text)
        # did + past-tense form ("we didn't broke") -> do-support error
        if v.tag_ == "VBD" and any(lem(x) == "do" for x in auxs) and low(v) != lem(v) and lem(v) != "do":
            yield ("err_do_support_past", None, "error", v.text)

def d_passive(s):
    for t in s:
        if t.dep_ in ("nsubjpass", "auxpass"):
            head = t.head
            yield ("b2_passive", "B2", "use", " ".join(x.text for x in s[head.left_edge.i - s.start: head.i - s.start + 1][-4:]))
            break

def d_modals(s):
    for t in s:
        if t.tag_ != "MD": continue
        m = low(t)
        head = t.head
        nxt = s.doc[t.i + 1] if t.i + 1 < len(s.doc) else None
        # modal + have + VBN = past speculation / regret
        if any(low(c) == "have" for c in head.children if c.dep_ == "aux") and head.tag_ == "VBN":
            yield ("b2_modals_speculation_past", "B2", "use", t.text + " have " + head.text)
            continue
        if m in ("might", "may", "could", "must") and lem(head) == "be":
            yield ("b1_modals_deduction_present", "B1", "use", t.text + " be")
        if m in ("should", "ought"):
            yield ("a2_have_to_should", "A2", "use", t.text + " " + head.text)
        if m in ("will", "'ll"):
            yield ("b1_will_vs_going_to", "B1", "use", t.text + " " + head.text)
        if nxt is not None and low(nxt) == "to":
            yield ("err_modal_plus_to", None, "error", t.text + " to")
    for t in s:
        if lem(t) == "have" and t.i + 1 < len(s.doc) and low(s.doc[t.i + 1]) == "to" and t.pos_ in ("VERB", "AUX"):
            yield ("a2_have_to_should", "A2", "use", "have to")
        if low(t) == "going" and t.i + 1 < len(s.doc) and low(s.doc[t.i + 1]) == "to" \
           and t.i + 2 < len(s.doc) and s.doc[t.i + 2].tag_ == "VB":
            yield ("a2_going_to", "A2", "use", "going to " + s.doc[t.i + 2].text)

def d_conditionals(s):
    ifs = [t for t in s if low(t) == "if" and t.dep_ == "mark"]
    for i in ifs:
        clause_v = i.head
        main_v = clause_v.head if clause_v.dep_ == "advcl" else None
        ca = [low(x) for x in aux_children(clause_v)]
        ma = [low(x) for x in aux_children(main_v)] if main_v is not None else []
        if "had" in ca and clause_v.tag_ == "VBN":
            yield ("c1_third_mixed_conditional", "C1", "use", "if ... had " + clause_v.text)
        elif clause_v.tag_ == "VBD" or "were" in ca or low(clause_v) == "were":
            if any(x in ("would", "could", "might", "'d") for x in ma):
                yield ("b2_second_conditional", "B2", "use", "if ... " + clause_v.text + " / would")
            else:
                yield ("b1_first_conditional", "B1", "use", "if + past (check)")
        else:
            yield ("b1_first_conditional", "B1", "use", "if " + clause_v.text)

def d_relatives(s):
    for t in s:
        if t.dep_ == "relcl" and not any(low(c) == "to" and c.dep_ == "aux" for c in t.children) \
           and not (lem(t) == "know" and any(low(c) == "you" for c in t.children)):
            pron = [c for c in t.children if low(c) in ("who", "which", "that", "whom", "whose", "where", "when")]
            p = pron[0] if pron else None
            nondef = p is not None and p.i > 0 and s.doc[p.i - 1].text == ","
            if nondef or (p is not None and low(p) == "which" and p.i > 0 and s.doc[p.i - 1].text == ","):
                yield ("b2_non_defining_relative", "B2", "use", t.head.text + ", " + (p.text if p else "") + " " + t.text)
            else:
                yield ("b1_defining_relative", "B1", "use", t.head.text + " " + (p.text if p else "Ø") + " " + t.text)

CAUSATIVE = {"make", "let", "have", "get", "help", "allow", "force", "cause", "enable"}
def d_causatives(s):
    for v in s:
        if lem(v) not in CAUSATIVE or v.pos_ != "VERB": continue
        nx = s.doc[v.i + 1] if v.i + 1 < len(s.doc) else None
        if lem(v) == "let" and nx is not None and low(nx) in ("'s", "us", "me"): continue
        comps = [c for c in v.children if c.dep_ in ("ccomp", "xcomp")]
        dobj = [c for c in v.children if c.dep_ in ("dobj", "nsubj") and c.i > v.i]
        for c in comps:
            subj = [x for x in c.children if x.dep_ in ("nsubj", "nsubjpass")]
            has_to = any(low(x) == "to" and x.dep_ == "aux" for x in c.children)
            if lem(v) in ("make", "let", "have") and (subj or dobj):
                if has_to:
                    yield ("err_causative_to", None, "error", v.text + " ... to " + c.text)
                elif c.tag_ in ("VB", "VBN"):
                    yield ("c1_causative_sophisticated" if c.tag_ == "VBN" else "b1_causative_basic",
                           "C1" if c.tag_ == "VBN" else "B1", "use", v.text + " ... " + c.text)
            elif lem(v) in ("get", "help", "allow", "force", "cause", "enable") and (subj or dobj):
                if c.tag_ == "VBN" and lem(v) == "get":
                    yield ("c1_causative_sophisticated", "C1", "use", "get ... " + c.text)
                elif has_to or lem(v) == "help":
                    yield ("b1_causative_basic", "B1", "use", v.text + " ... " + c.text)

def d_comparison(s):
    txt = s.text.lower()
    for t in s:
        if t.tag_ in ("JJR", "RBR") and low(t) not in ("more", "less") or \
           (low(t) in ("more", "less") and t.i + 1 < len(s.doc) and s.doc[t.i + 1].tag_ in ("JJ", "RB")):
            yield ("a2_comparatives", "A2", "use", t.text)
            break
    for t in s:
        if (t.i > 0 and low(s.doc[t.i-1]) == "at") or (t.i + 1 < len(s.doc) and low(s.doc[t.i+1]) == "of"): continue
        if t.tag_ in ("JJS", "RBS") or (low(t) == "most" and t.i + 1 < len(s.doc) and s.doc[t.i + 1].tag_ == "JJ"):
            yield ("a2_comparatives", "A2", "use", t.text)
            break
    if re.search(r"\bas (\w+ ){1,3}as\b", re.sub(r"\bas (far|well|long|soon) as\b", "", txt)):
        yield ("old_as_as", "B1", "use", re.search(r"\bas (\w+ ){1,3}as\b", re.sub(r"\bas (far|well|long|soon) as\b", "", txt)).group(0))

def d_structures(s):
    txt = s.text.lower()
    toks = [low(t) for t in s]
    if re.search(r"\bi wish\b", txt):
        yield ("c1_hypothetical_language", "C1", "use", "I wish")
    if re.search(r"\b(it's|it is|it was) (high |about )?time (i|you|we|they|he|she) \w+ed\b", txt) or re.search(r"\bwould rather\b", txt):
        yield ("c1_hypothetical_language", "C1", "use", re.search(r"(time|rather)", txt).group(0))
    if re.search(r"^(what (i|we|you) \w+ (is|was))", txt) or re.search(r"\bit (is|was|'s) (\w+ ){1,3}(that|who) ", txt) \
       and not re.search(r"\bit (is|was|'s) (not )?(the )?(same|so|too)\b", txt):
        yield ("c1_cleft_sentences", "C1", "use", "cleft?")
    if re.search(r"\b(not only|never have|rarely|seldom|no sooner|hardly had|little did)\b", txt):
        yield ("c1_inversion_emphasis", "C1", "use", "inversion?")
    for t in s:
        if lem(t) == "do" and t.dep_ == "aux" and t.head.tag_ == "VB" and \
           not any(c.dep_ == "neg" for c in t.head.children) and t.i > s.start and \
           not s.text.strip().endswith("?") and low(t) in ("do", "does", "did"):
            yield ("c1_emphatic_do", "C1", "use", t.text + " " + t.head.text)
    for t in s:
        if t.dep_ == "advcl" and t.tag_ in ("VBG", "VBN") and (t.left_edge.i == s.start or s.doc[t.left_edge.i-1].text == ",") and not any(c.dep_.startswith("nsubj") or c.dep_ == "mark" for c in t.children):
            yield ("c1_participle_clauses", "C1", "use", t.text)
            break
    if re.search(r"\b(it is|it's) (said|believed|thought|reported|known) (that|to)\b", txt) or \
       re.search(r"\b(is|are|was|were) (said|believed|thought|reported|supposed) to\b", txt):
        yield ("c1_advanced_passive_reporting", "C1", "use", "reporting passive")
    for t in s:
        if lem(t) in ("say", "tell", "ask", "mention", "explain") and t.tag_ in ("VBD", "VBN") and \
           any(c.dep_ == "ccomp" for c in t.children) and low(s[0]) != '"':
            yield ("b2_reported_speech", "B2", "use", t.text + " ...")
            break
    # despite + finite clause  ("despite it's short") -> error
    for t in s:
        if low(t) in ("despite", "in spite") and t.i + 2 < len(s.doc):
            nxt = s.doc[t.i + 1: t.i + 3]
            if any(x.pos_ in ("PRON",) for x in nxt[:1]) and any(x.pos_ in ("AUX", "VERB") for x in nxt):
                yield ("err_despite_clause", None, "error", "despite " + nxt.text)
            else:
                yield ("b2_advanced_connectors", "B2", "use", "despite")

def d_agreement(s):
    for v in s:
        subj = [c for c in v.children if c.dep_ == "nsubj"]
        if not subj: continue
        sj = subj[0]
        # plural noun subject + singular verb ("the patterns is", "files which doesn't")
        target = v
        auxs = [a for a in v.children if a.dep_ in ("aux",) and a.i < v.i]
        if any(a.tag_ == "MD" for a in auxs): continue
        if any(lem(a) == "do" and a.i < sj.i for a in v.children): continue      # question: "did something ... make"
        if any(c.dep_ == "conj" for c in sj.children): continue                # compound subject
        if auxs: target = auxs[0]
        if target.i - sj.i > 4 and low(sj) not in ("which", "that", "who"): continue
        if lem(target) == "do" and target.i - sj.i > 1: continue              # "my list so don't worry"
        if sj.tag_ == "NNS" and target.tag_ == "VBZ":
            yield ("err_subject_verb_agreement", None, "error", sj.text + " " + target.text)
        if sj.tag_ in ("NN", "NNP") and target.tag_ == "VBP" and low(target) not in ("'m",):
            yield ("err_subject_verb_agreement", None, "error", sj.text + " " + target.text)
        if low(sj) in ("which", "that", "who") and sj.head.head.tag_ == "NNS" and target.tag_ == "VBZ":
            yield ("err_subject_verb_agreement", None, "error", sj.head.head.text + " " + sj.text + " " + target.text)

LEXICAL_ERRORS = [
    (r"\bcome across that\b", "err_collocation", "come across that -> come across as"),
    (r"\bdespite of\b", "err_collocation", "despite of"),
    (r"\bdiscuss about\b", "err_collocation", "discuss about"),
    (r"\bexplain (me|him|her|us|them)\b", "err_collocation", "explain + person"),
    (r"\b(let|make) (me|him|her|us|them|it) to\b", "err_causative_to", "let/make + obj + to"),
    (r"\b(can|could|should|must|might|will|would) to\b", "err_modal_plus_to", "modal + to"),
]
def d_errors(s):
    txt = s.text.lower()
    for rx, concept, label in LEXICAL_ERRORS:
        for m in re.finditer(rx, txt):
            yield (concept, None, "error", m.group(0))
    toks = list(s)
    for i, t in enumerate(toks[:-1]):
        nx = toks[i + 1]
        nx2 = toks[i + 2] if i + 2 < len(toks) else None
        # "it's belongs", "it's just give"  -> be + finite verb
        if low(t) in ("'s", "is", "am", "'m", "are", "'re") and t.pos_ == "AUX" and not (i > 0 and lem(toks[i-1]) == "let"):
            v = nx2 if (low(nx) in ("just", "also", "really", "originally", "always", "only") and nx2 is not None) else nx
            if v is not None and v.tag_ in ("VBZ", "VBP") and lem(v) not in ("be", "have", "do", "get") \
               and v.dep_ not in ("aux",):
                yield ("err_be_plus_finite_verb", None, "error", t.text + " " + v.text)
    # "it's just give you" -> be + bare verb after an adverb
    for i, t in enumerate(toks[:-2]):
        if low(t) in ("'s", "is") and not (i > 0 and lem(toks[i-1]) == "let") and low(toks[i+1]) in ("just", "also", "really", "only", "always") \
           and toks[i+2].tag_ == "VB":
            yield ("err_be_plus_finite_verb", None, "error", t.text + " " + toks[i+1].text + " " + toks[i+2].text)
    # -ed / -ing emotion adjectives ("it was frustrated for me", "I am boring")
    for m in re.finditer(r"\b(it|this|it's)( (was|is|'s|were))? (\w+ ){0,3}?(frustrat|bor|confus|excit|interest|tir|exhaust|annoy|disappoint|surpris|embarrass|overwhelm)ed\b", txt):
        yield ("err_ed_ing_adjective", None, "error", m.group(0))
    for m in re.finditer(r"\b(i|i'm|i am|we|we're|we are)( (was|am|were|'m|'re|are|feel|felt))? (\w+ ){0,3}?(boring|confusing|exciting|interesting|tiring|annoying|disappointing|embarrassing|frustrating)\b", txt):
        yield ("err_ed_ing_adjective", None, "error", m.group(0))
    # number agreement with be/have
    for v in s:
        subj = [c for c in v.children if c.dep_ in ("nsubj", "nsubjpass", "expl")]
        if not subj: continue
        sj = subj[0]
        verbs = [v] + [a for a in v.children if a.dep_ in ("aux", "auxpass") and a.i < v.i]
        if any(a.tag_ == "MD" for a in verbs): continue                       # "should have"
        for x in verbs:
            if sj.tag_ == "NN" and low(x) in ("were", "are", "have") and \
               not any(low(c) == "if" for c in v.children) and sj.i < x.i:
                yield ("err_subject_verb_agreement", None, "error", sj.text + " ... " + x.text)
            if sj.tag_ == "NNS" and low(x) in ("was", "is", "has") and sj.i < x.i:
                yield ("err_subject_verb_agreement", None, "error", sj.text + " ... " + x.text)

CONNECTORS = [
    # (regex, concept, level)
    (r"\b(because|so that)\b", "a_basic_connectors", "A2"),
    (r"\bbut\b", "a_basic_connectors", "A2"),
    (r"\beven though\b", "b1_concessive_connectors", "B1"),
    (r"(?<!even )\b(although|though)\b", "b1_concessive_connectors", "B1"),
    (r"\bwhereas\b|\bwhile\b(?= (i|you|he|she|we|they|it|the|this|[a-z]+ing)\b)", "b1_concessive_connectors", "B1"),
    (r"\bunless\b", "b1_concessive_connectors", "B1"),
    (r"\bhowever\b", "b1_however", "B1"),
    (r"\botherwise\b", "b1_however", "B1"),
    (r"\b(moreover|furthermore|nevertheless|on the other hand|in addition|as a result|therefore|in spite of)\b", "b2_advanced_connectors", "B2"),
    (r"\b(nonetheless|notwithstanding|albeit|hence|thus|consequently|by contrast|that said|having said that|to be fair|all things considered|in the meantime|at the end of the day|as far as i (understand|know|can tell)|in short)\b", "c1_discourse_markers", "C1"),
    (r"\bregardless of\b", "c1_sophisticated_linking", "C1"),
    (r"\bthroughout\b", "c1_sophisticated_linking", "C1"),
]
OLD_TRACKED = [
    (r"\beven\b(?! though)", "old_even"),
    (r"\bthrough\b", "old_through"),
    (r"\banything to do with\b", "old_anything_to_do_with"),
    (r"\b(much )?more likely to\b", "old_more_likely_to"),
    (r"\bforces? (\w+ )?to\b", "old_force_to"),
    (r"\blead(s)? to\b|\bled to\b", "old_lead_to"),
    (r"\bdeeply enough\b", "old_reflect_deeply_enough"),
]
def d_connectors(s):
    txt = s.text.lower()
    for rx, concept, lvl in CONNECTORS:
        for m in re.finditer(rx, txt):
            yield (concept, lvl, "use", m.group(0))
    for rx, concept in OLD_TRACKED:
        for m in re.finditer(rx, txt):
            yield (concept, None, "use", m.group(0))

DETECTORS = [d_tenses, d_passive, d_modals, d_conditionals, d_relatives,
             d_causatives, d_comparison, d_structures, d_agreement, d_errors, d_connectors]

# ------------------------------------------------ range ends (A1 and C2), added 25.09
# Run as a second pass AFTER the original detectors, so the indices of earlier
# candidates never shift (verdicts written against them stay valid).
def d_a1(s):
    for t in s:
        if t.pos_ == "VERB" and t.tag_ in ("VBZ", "VBP") and not aux_children(t):
            yield ("a1_present_simple", "A1", "use", t.text); break
    for t in s:
        if t.pos_ == "VERB" and t.tag_ == "VBD" and not aux_children(t):
            yield ("a2_past_simple", "A2", "use", t.text); break
    for t in s:
        if low(t) in ("can", "ca") and t.tag_ == "MD":
            yield ("a1_can", "A1", "use", t.text); break
    for t in s:
        if t.dep_ == "expl" and low(t) == "there":
            yield ("a1_there_is_are", "A1", "use", "there " + t.head.text); break

HEDGES = r"\b(would seem|would appear|it seems to me|arguably|might well|may well|could well|to some extent|to a certain extent|it could be argued|i would argue|i'd argue|i tend to think|so to speak|as it were|by and large|if anything)\b"
CONCESSION_C2 = r"(?<!as )\b(much as (i|we|you|he|she|they)|be that as it may|not that (i|it|he|she|we|they|you)\b|come what may|for all (his|her|their|my|its|the)\b|however (much|hard|good|bad) (i|you|we|they|he|she|it)\b)"
SUBJ_HEADS = {"suggest", "insist", "recommend", "demand", "propose", "request", "ask", "essential", "vital", "important", "crucial", "imperative", "necessary"}

def clause_depth(tok):
    d, t = 0, tok
    while t.head.i != t.i:
        if t.dep_ in ("advcl", "ccomp", "relcl", "acl") and t.pos_ in ("VERB", "AUX") and \
           any(c.dep_ == "mark" or c.tag_ in ("WDT", "WP", "WRB") for c in t.children):
            d += 1          # only clauses opened by an explicit subordinator (because/that/if/which/who...)
        t = t.head
    return d

def d_c2(s):
    txt = s.text.lower()
    if (re.search(r"^(had|were|should) (i|you|he|she|we|they|it|the \w+) \w+", txt) and not txt.rstrip().endswith("?")) or \
       re.search(r"[,;] (had|were|should) (i|you|he|she|we|they) (\w+ )?(known|to|need|have|been|there)\b", txt):
        yield ("c2_conditional_inversion", "C2", "use", "had/were/should + subject")
    for m in re.finditer(HEDGES, txt):
        yield ("c2_hedged_modality", "C2", "use", m.group(0))
    for m in re.finditer(CONCESSION_C2, txt):
        yield ("c2_advanced_concession", "C2", "use", m.group(0))
    for t in s:
        base_passive = t.tag_ == "VBN" and any(low(c) == "be" and c.dep_ == "auxpass" for c in t.children)
        if (t.tag_ == "VB" or base_passive) and t.dep_ == "ccomp" and lem(t.head) in SUBJ_HEADS and \
           any(low(c) == "that" and c.dep_ == "mark" for c in t.children) and \
           not any(c.dep_ == "aux" for c in t.children):
            subj = [c for c in t.children if c.dep_ in ("nsubj", "nsubjpass")]
            if subj and (subj[0].tag_ in ("NN", "NNP") or low(subj[0]) in ("he", "she", "it") or lem(t) == "be" or base_passive):
                yield ("c2_subjunctive", "C2", "use", lem(t.head) + " that ... " + t.text)
    if re.search(r"\bthe (more|less|better|worse|sooner|longer|harder|bigger|faster)\b.{1,60}\bthe (more|less|better|worse|sooner|longer|harder|bigger|faster)\b", txt):
        yield ("c1_comparative_correlative", "C1", "use", "the more ..., the more ...")
    if len(s) <= 45 and max((clause_depth(t) for t in s), default=0) >= 3:
        yield ("c2_stacked_subordination", "C2", "use", "3+ nested clauses")

DETECTORS_V2 = [d_a1, d_c2]

# ------------------------------------------ B2-C2 expansion, batch 1 (added 26.09)
# Selected from the English Grammar Profile (Cambridge): B2-C2 points that a parser or a
# word pattern can spot reliably. Third pass, after DETECTORS_V2, so earlier indices never shift.
# EGP numbers in brackets are for reference only.
BE_FORMS = r"(?:am|is|are|was|were|be|been|being|'m|'re|'s|isn't|aren't|wasn't|weren't)"
V3_PATTERNS = [
    # (regex on the lowercased sentence, concept, level)
    (BE_FORMS + r" (?:\w+ )?(?:supposed|meant) to\b", "b2_be_supposed_meant_to", "B2"),        # 475-477
    (BE_FORMS + r" (?:\w+ )?(?:likely|unlikely|bound|certain) to\b", "b2_be_likely_bound_to", "B2"),  # 473, 478, 480
    (BE_FORMS + r" (?:just )?(?:about|due) to (?!the\b|a\b|an\b|this\b|that\b|his\b|her\b|my\b|our\b|their\b|its\b|some\b)\w+", "b2_be_about_due_to", "B2"),                 # 360-363
    (r"\bboth (?!of\b).{1,40}\band\b", "b2_paired_conjunctions", "B2"),                          # 269
    (r"\bneither\b .{1,40}\bnor\b|\beither\b .{1,40}\bor\b|\bnot only\b .{1,60}\bbut\b", "b2_paired_conjunctions", "B2"),  # 268, 271, 176
    (r"\bas (?:if|though)\b", "b2_as_if_as_though", "B2"),                                     # 165
    (r"\brather than\b", "b2_rather_than", "B2"),                                              # 164
    (r"\bthe (?:thing|point|problem|fact|reason|issue|truth|question) (?:is|was),? (?:that|i|you|we|they|he|she|it|there|how|what|why|whether|when|if|will|can|do)\b", "b2_the_thing_is", "B2"),  # 1163-1164
    (r"\b(?:as long as|provided that|providing that|in case(?! of\b)|even if|now that|given that|as soon as(?! possible\b)|in order that|despite the fact that)\b", "b2_complex_conjunctions", "B2"),  # 279-280, 1119
    (r"\b\w+ enough to\b", "b2_adjective_enough_to", "B2"),                                    # 40, 162
    (r"\bstill (?:haven't|hasn't|have not|has not|didn't|did not)\b", "b2_still_negative_perfect", "B2"),  # 832
    (r"\b(?:neither|none|either) of (?:them|us|you|these|those|the|my|our|your|his|her|their)\b", "b2_neither_none_of", "B2"),  # 1195
    (r"\bi (?:was wondering|wondered|was hoping|wanted to ask) (?:if|whether|about)\b", "b2_polite_past", "B2"),  # 753, 802
    (r"\bnot necessarily\b", "c1_not_necessarily", "C1"),                                      # 644-645
    (r"\bnot (?:all|every|everyone|everybody|everything)\b", "c1_not_all_every", "C1"),        # 1197
    (r"\b(?:whatsoever|in the least|in the slightest|by no means|by any means)\b", "c1_negative_emphasis", "C1"),  # 1201, 1205
    (r"(?:^|[,;] )(?:whatever|wherever|whenever|whoever|no matter (?:what|how|who|where|when)) (?:i|you|we|they|he|she|it|the|this|that|your|my|our|people)\b", "c1_wh_ever_clauses", "C1"),  # 281
    (r"\b(?:might|may) (?:just )?as well\b", "c2_might_as_well", "C2"),                        # 511, 528
    (BE_FORMS + r" (?:always|constantly|forever|continually) \w+ing\b", "c2_continuous_always", "C2"),  # 754, 863
    (r"\bwhether or not\b|\bwhether (?:\w+ ){1,6}or not\b", "c2_whether_or_not", "C2"),        # 1131
    (r"\b(?:so long as|on condition that|in the event (?:that|of)|supposing (?:that )?(?:i|you|we|they|he|she|it))\b", "c2_formal_conditions", "C2"),  # 1127
    (r"\b(?:if it (?:weren't|wasn't|were not|was not|hadn't been|had not been) for|had it not been for|were it not for)\b", "c2_if_it_werent_for", "C2"),  # 782, 1128-1129
    (r"\bin that (?:i|you|we|they|he|she|it|the|this|there|people)\b", "c2_in_that", "C2"),   # 282
]

def d_v3_patterns(s):
    txt = s.text.lower()
    for rx, concept, lvl in V3_PATTERNS:
        m = re.search(rx, txt)
        if m:
            yield (concept, lvl, "use", m.group(0)[:40])

def d_v3_verbs(s):
    for v in s:
        if v.pos_ not in ("VERB", "AUX"): continue
        auxs = aux_children(v)
        a = [low(x) for x in auxs]
        md = [x for x in auxs if x.tag_ == "MD"]
        # will/'ll be + -ing (future continuous)                                         # 358
        if v.tag_ == "VBG" and md and low(md[0]) in ("will", "'ll", "wo") and "be" in a:
            yield ("b2_future_continuous", "B2", "use", "will be " + v.text)
        # will have + -ed (future perfect)                                                 # 377
        if v.tag_ == "VBN" and md and low(md[0]) in ("will", "'ll", "wo") and "have" in a and "been" not in a:
            yield ("b2_future_perfect", "B2", "use", "will have " + v.text)
        # had been + -ing (past perfect continuous)                                        # 758-762
        if v.tag_ == "VBG" and "been" in a and any(x in ("had", "'d") for x in a) and not md:
            yield ("b2_past_perfect_continuous", "B2", "use", "had been " + v.text)
        # passive with a modal or 'have to': can be done, has to be done                  # 715, 725
        if v.tag_ == "VBN" and any(x.dep_ == "auxpass" and lem(x) == "be" for x in v.children) and lem(v) != "rid" and \
           (md or any(low(x) == "to" and x.dep_ == "aux" for x in v.children)) and "have" not in a:
            yield ("b2_passive_modal", "B2", "use", (low(md[0]) if md else "to") + " be " + v.text)
        # perfect passive: has/have/had been + -ed                                         # 718, 723
        if v.tag_ == "VBN" and any(low(x) == "been" and x.dep_ == "auxpass" for x in v.children) and \
           any(x in ("has", "have", "had", "'ve", "'s", "'d") for x in a):
            yield ("b2_passive_perfect", "B2", "use", "been " + v.text)
        # negative modal perfect: can't / couldn't / might not / needn't have + -ed      # 452, 510, 523, 553
        if v.tag_ == "VBN" and md and "have" in a and any(c.dep_ == "neg" for c in v.children):
            yield ("c1_negative_modal_perfect", "C1", "use", low(md[0]) + " not have " + v.text)

def d_v3_clauses(s):
    txt = s.text.lower()
    # relative 'whose'                                                                    # 237-238
    for t in s:
        if low(t) == "whose" and t.i > s.start and not s.text.strip().endswith("?"):
            yield ("b2_relative_whose", "B2", "use", "whose " + t.head.text); break
    # preposition + which/whom inside a relative clause ("the way in which", "to whom")  # 848
    for t in s:
        if t.pos_ == "ADP" and t.dep_ != "prt" and t.i > s.start and t.i + 1 < s.end and low(s.doc[t.i + 1]) in ("which", "whom") \
           and s.doc[t.i - 1].pos_ in ("NOUN", "PROPN", "PRON") \
           and not s.text.strip().endswith("?"):
            yield ("b2_preposition_relative", "B2", "use", t.text + " " + s.doc[t.i + 1].text); break
    # superlative + (noun) + that/I + ever                                                # 161
    if re.search(r"\b(?:the )?(?:\w+est|best|worst|most \w+|least \w+) (?:\w+ ){0,3}(?:that |which |who )?(?:i|we|you|they|he|she)(?: have| had|'ve|'d)? ever\b", txt):
        yield ("b2_superlative_ever", "B2", "use", "superlative ... ever")

DETECTORS_V3 = [d_v3_patterns, d_v3_verbs, d_v3_clauses]

# ------------------------------------------ B2-C2 expansion, batch 2 (added 26.09)
# Parser-dependent points from the English Grammar Profile. Fourth pass, after
# DETECTORS_V3, so earlier indices never shift. EGP numbers for reference only.
REPORTED_Q = r"\b(?:asked|wondered|wanted to know|didn't know|did not know|had no idea)(?: (?:me|him|her|them|us|you|myself))? (?:if|whether|what|why|how|when|where|who)\b"   # 778
NEG_Q = r"(?:^|[,;] |\b(?:so|but|and|well|why|oh) )(?:don't|doesn't|didn't|isn't|aren't|wasn't|weren't|won't|wouldn't|couldn't|shouldn't|can't|haven't|hasn't) (?:you|it|we|they|he|she|i|that|this|there)\b"  # 218, 886-887
IT_ADJ_THAT = r"\bit(?:'s| is| was| seems| seemed| appears| appeared| looks| looked| became| becomes)(?: (?:quite|very|pretty|really|so|more|fairly|highly|absolutely|not|clear|kind of|a bit))? (?:obvious|clear|likely|unlikely|possible|impossible|important|true|strange|funny|interesting|surprising|essential|crucial|necessary|vital|evident|apparent|unfair|fair|natural|odd|weird|sad|lucky|amazing|annoying|ironic|good|bad|great|nice|a shame|a pity|no wonder|no surprise) that\b"  # 430-433
MUST_SAY = r"\bi (?:must|have to|'ve got to|have got to|gotta) (?:say|admit|confess)\b"          # 542, 544
YET_CONC = r"(?:[,;] (?:and |but )?|^(?:and |but )?)yet(?:,)? (?:i|you|we|they|he|she|it|the|this|there|people|my|our|his|her|their|nobody|no one|still)\b"  # 270, 275
STANCE = {"apparently", "admittedly", "inevitably", "undoubtedly", "understandably", "interestingly",
          "surprisingly", "unsurprisingly", "ironically", "frankly", "presumably", "supposedly", "evidently",
          "predictably", "curiously", "regrettably"}          # 109
EXTREME = {"absolutely", "utterly", "totally", "completely", "incredibly", "extremely", "remarkably",
           "exceptionally", "thoroughly", "entirely", "deeply", "highly", "immensely", "hugely"}       # 42, 107
CMP_MOD = {"much", "far", "slightly", "way", "considerably", "significantly", "substantially", "somewhat"}  # 26-28, 125
OBJ_PRON = {"me", "him", "her", "it", "them", "us", "you", "this", "that"}
PV_PREPS = {"with", "to", "on", "at", "of", "for", "against", "into", "about"}
V4_SEEN = set()   # phrasal-verb structures count once per verb per session (the phrasal verb list tracks every use)

def d_v4_patterns(s):
    txt = s.text.lower()
    for rx, concept, lvl in ((REPORTED_Q, "b2_reported_questions", "B2"), (NEG_Q, "b2_negative_questions", "B2"),
                             (IT_ADJ_THAT, "b2_it_adjective_that", "B2"), (MUST_SAY, "b2_i_must_say_admit", "B2"),
                             (YET_CONC, "c1_yet_concessive", "C1")):
        m = re.search(rx, txt)
        if m:
            yield (concept, lvl, "use", m.group(0).strip(" ,;")[:40])
    # comparative modifiers: much / far / slightly / a lot / a bit + comparative; by far + superlative
    m = re.search(r"\bby far (?:the )?(?:\w+est|best|worst|most \w+)\b|\b(?:a lot|a bit|a little|lots) (?:more \w+|\w+er)\b", txt)
    if m:
        yield ("b2_comparative_modifiers", "B2", "use", m.group(0))
    else:
        for t in s:
            if low(t) in CMP_MOD and t.i + 1 < s.end:
                nx = s.doc[t.i + 1]
                if nx.tag_ in ("JJR", "RBR") and low(nx) not in ("more", "less") or \
                   (low(nx) in ("more", "less") and t.i + 2 < s.end and s.doc[t.i + 2].pos_ in ("ADJ", "ADV")):
                    yield ("b2_comparative_modifiers", "B2", "use", t.text + " " + nx.text); break

def d_v4_parse(s):
    # stranded preposition: "the person I talked to", "what are you worried about"               # 1050
    for t in s:
        if t.pos_ == "ADP" and t.dep_ == "prep" and not list(t.children) and t.head.pos_ in ("VERB", "ADJ") and \
           (t.i + 1 >= s.end or s.doc[t.i + 1].is_punct or s.doc[t.i + 1].pos_ in ("CCONJ", "SCONJ")) and \
           (t.head.dep_ in ("relcl", "acl") or (t.head.dep_ == "xcomp" and t.head.head.dep_ in ("relcl", "acl")) or
            low(s[0]) in ("what", "who", "which", "where", "whom")):
            yield ("b2_stranded_preposition", "B2", "use", t.head.text + " ... " + t.text); break
    for v in s:
        if v.pos_ != "VERB": continue
        prts = [c for c in v.children if c.dep_ == "prt"]
        for p in prts:
            # phrasal-prepositional verb: come up with, look forward to, get along with                # 1045
            nx = s.doc[p.i + 1] if p.i + 1 < len(s.doc) else None
            if nx is not None and nx.pos_ == "ADP" and nx.dep_ == "prep" and nx.head.i in (v.i, p.i) and \
               low(nx) in PV_PREPS and ("ppv", v.lemma_, low(p), low(nx)) not in V4_SEEN:
                V4_SEEN.add(("ppv", v.lemma_, low(p), low(nx)))
                yield ("b2_phrasal_prepositional_verb", "B2", "use", f"{v.lemma_} {p.text} {nx.text}")
            # object pronoun between verb and particle: pick her up, figure it out                     # 1065
            if p.i == v.i + 2 and low(s.doc[v.i + 1]) in OBJ_PRON and ("split", v.lemma_, low(p)) not in V4_SEEN:
                V4_SEEN.add(("split", v.lemma_, low(p)))
                yield ("c1_split_phrasal_pronoun", "C1", "use", f"{v.text} {s.doc[v.i + 1].text} {p.text}")
    # stance adverbs at clause level ("Apparently, ...", "..., admittedly, ...")                    # 109
    for t in s:
        if low(t) in STANCE and t.dep_ == "advmod" and t.head.pos_ in ("VERB", "AUX") and \
           (t.i == s.start or s.doc[t.i - 1].is_punct or (t.i + 1 < s.end and s.doc[t.i + 1].is_punct)):
            yield ("c1_stance_adverbs", "C1", "use", t.text); break
    # extreme / degree adverb + adjective ("absolutely exhausted", "utterly different")           # 42, 107
    for t in s:
        if low(t) in EXTREME and t.dep_ == "advmod" and t.head.pos_ == "ADJ" and t.head.i == t.i + 1:
            yield ("c1_extreme_adverbs", "C1", "use", t.text + " " + t.head.text); break

DETECTORS_V4 = [d_v4_patterns, d_v4_parse]

# High-volume, near-zero-risk concepts: accepted as correct without line-by-line
# review (a misparse here can't produce a false error, only a harmless extra use).
AUTO_ACCEPT = {"a_basic_connectors", "b1_will_vs_going_to", "a1_present_simple", "a2_past_simple", "a1_can", "a1_there_is_are"}

def main(inp, out):
    cands, words, by_mode, docs = [], 0, {"voice": 0, "typed": 0}, []
    for turn, raw, mode in load_turns(inp):
        text = clean(raw)
        n = len(re.findall(r"[A-Za-z']+", text))
        words += n; by_mode[mode] += n
        docs.append((turn, mode, nlp(text)))
    for detectors in (DETECTORS, DETECTORS_V2, DETECTORS_V3, DETECTORS_V4):
        for turn, mode, doc in docs:
            for s in doc.sents:
                if len(s) < 3: continue
                seen = set()
                for d in detectors:
                    for concept, level, kind, match in d(s):
                        key = (concept, match.lower())
                        if key in seen: continue
                        seen.add(key)
                        cands.append({"i": len(cands), "turn": turn, "mode": mode, "concept": concept, "level": level,
                                      "kind": kind, "match": match, "sentence": s.text.strip()})
    json.dump({"words": words, "words_by_mode": by_mode, "candidates": cands}, open(out, "w"), indent=1, ensure_ascii=False)
    auto = [c for c in cands if c["concept"] in AUTO_ACCEPT]
    print(f"{words} words (voice {by_mode['voice']}, typed {by_mode['typed']}) · {len(cands)} candidates · {len(auto)} auto-accepted ({', '.join(sorted(AUTO_ACCEPT))})")
    print("REVIEW LIST  (index | kind | concept | match | sentence)")
    for c in cands:
        if c["concept"] in AUTO_ACCEPT: continue
        print(f'{c["i"]:4} | {c["kind"]:5} | {c["concept"]} | {c["match"]} | {c["turn"]} {c["mode"][0]}: {c["sentence"][:170]}')

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
