#!/usr/bin/env python3
"""
Unique words (added 29.09.26): the running set of different words Murat has used,
by base form (lemma), from 29.09.26 on. Stored in meta/lexicon as
{"since": date, "as_of": date, "sessions": [doc_id, ...], "words": {lemma: index into sessions}}.

Adds this session's new lemmas and writes vocab.unique = {session, new, total} into the
session doc. Idempotent per doc_id: a rerun in the same chat gives the same numbers.

Usage: python3 lex_apply.py meta/lexicon.json vocab_candidates.json session_doc.json <doc_id> lexicon_out.json
"""
import json, os, re, sys

FILL = re.compile(r"^(u+h+m*|u+m+|m{2,}|h+m+|e+r+m*|e+h+m*|a+h+)$")

def main(lex_path, vc_path, sess_path, doc_id, out):
    lex = {"since": None, "as_of": None, "sessions": [], "words": {}}
    if os.path.exists(lex_path):
        d = json.load(open(lex_path)); lex = d.get("data", d)
    vc = json.load(open(vc_path)); doc = json.load(open(sess_path))
    lemmas = sorted({w for w in vc.get("lemmas", []) if w.isalpha() and not FILL.match(w)})
    if doc_id not in lex["sessions"]: lex["sessions"].append(doc_id)
    idx = lex["sessions"].index(doc_id)
    new = 0
    for w in lemmas:
        if w not in lex["words"]:
            lex["words"][w] = idx; new += 1
        elif lex["words"][w] == idx:
            new += 1          # first seen in this same session (rerun)
    lex["since"] = lex["since"] or doc["date"]; lex["as_of"] = doc["date"]
    doc.setdefault("vocab", {})["unique"] = {"session": len(lemmas), "new": new, "total": len(lex["words"])}
    json.dump(doc, open(sess_path, "w"), indent=1, ensure_ascii=False)
    json.dump(lex, open(out, "w"), ensure_ascii=False)
    print(f"unique words: {len(lemmas)} this session · {new} new · {len(lex['words'])} in total since {lex['since']}")

if __name__ == "__main__":
    main(*sys.argv[1:6])
