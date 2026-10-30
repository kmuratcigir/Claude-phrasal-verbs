---
name: "reading-session"
description: "Run Murat's reading practice: he picks the list-word mix (or the default), Claude writes a 400-600 word passage slightly above his level with 12-18 of his own list words woven in, checks it with the CEFR tools, gives it to him, and logs it on the Fluency Ledger's Reading tab. Trigger on \"reading session\", \"let's do a reading practice\" or \"prepare a reading passage\" in My English Journey."
---

# Reading Session

Runs when Murat says "reading session", "let's do a reading practice" or "prepare a reading
passage". It replaces the step-by-step part of Project Instructions Section 6 (built 28.09.26).

Why it works this way (Murat's decisions, 28.09.26):
- **Exposure, not drilling.** The passage is real reading: no quiz, no comprehension
  questions, no vocabulary exercises. Optional short chat about words in context afterwards.
- **His own words, woven in.** 12-18 items from his study lists appear naturally in each
  passage (he chose normal length with 12-18 items over longer passages with 25-35). He
  mostly half-knows these words already (his Pattern 1 gap), so meeting them in context helps
  them surface in speech.
- **Slightly above his level**, to lift his ceiling: 12-22% of the content words at B2 or
  above, at least 3% at C1/C2, and at least 75% easy (A1-B1) words so it stays comfortable
  (~85-90% comprehension). Calibration, 28.09.26: a plain B2 text scored 1% B2+ / 99% easy; a
  demanding Economist-style C1 article scored 29% B2+ / 71% easy. Measured, never guessed.
- **Logged** in the ledger's `reading` collection, shown on the dashboard's Reading tab
  (last reading, readings per week against his target of 4, and which list words met in a
  passage he later used on his own in a practice session).
- **Reading never counts as a use or a review** of a word. Nothing in `meta/pv_tracker` or
  `meta/vocab_tracker` is changed by this skill.
- Murat chooses the word mix, as for vocab sessions; Claude never picks the mix for him. He can
  say "your pick", which means the default below.
- One question at a time. In voice mode, keep every turn short (Project Instructions Section 0).

Ledger: https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK (Fluency Ledger).

## The ledger's files (since 30.10.26)

The Fluency Ledger (https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK) keeps its data in **files
published inside the artifact**, not in its database. Chats lost the `ArtifactData` tool on
30.10.26, and the database tools left in chats (`db_get`, `db_write`, …) pass every document
through the conversation, far too costly for these files. The ledger's database is a frozen copy as of
29.10.26: never read or write it, even where `ArtifactData` or `db_*` tools are available. The files:

- `data/index.json`: the ids that exist (`sessions`, `reading`, `meta`).
- `data/meta/<name>.json`: `pv_tracker`, `vocab_tracker`, `prep_watch`, `lexicon`, `interference`,
  `chunks`, `overview`, `phave`, `registry`.
- `data/sessions/<doc_id>.json` (one per checked chat) and `data/reading/<doc_id>.json`.

**Reading.** Use the artifact file tools, so the content never enters the chat: in a chat,
`read_file` on the ledger (load the artifacts tools first if they aren't loaded; read several
paths per call when the tool allows); in Claude Code, `Artifact` `read` with `url` and `paths`.
Each file lands in the workspace and the tool says where: move it into the work folder at its
path without `data/` (`data/meta/pv_tracker.json` → `<work>/meta/pv_tracker.json`). Read
`data/index.json` first, and note the ledger's **version id** shown with it. Never print a file's
content into the chat, and never use `publish_version` or `edit_version` for data: they need the
content typed out.

**Saving: one publish, one approval.**
1. Stage with `ledger.py` (the command is in the step that saves). It compares every file with
   what was read, refuses the whole save if any list would lose a row, or a row would lose a date
   or a review, and adds new ids to `data/index.json`. On `REFUSED` nothing is staged: stop and
   tell Murat what it lists. Never work round it.
2. Check the ledger's current version id with the short call (chat: `get_artifact`, not a full
   file listing; Claude Code: `Artifact` `list` with scope `files`). If it differs from the one you
   noted, something was saved in between: read the files you change again, rerun the scripts that
   build them, stage again.
3. Publish exactly the files the `PUBLISH:` line lists, each at its `data/…` path, as a new version
   of the ledger. **In a chat**, `publish_files` only takes files from the chat's working folder
   (`/home/claude`) or uploads, never from `/tmp`: first
   `rm -rf /home/claude/publish && cp -r <work>/publish /home/claude/publish`, then `publish_files`
   from `/home/claude/publish` (e.g. `/home/claude/publish/data/meta/pv_tracker.json` published as
   `data/meta/pv_tracker.json`). Never send `index.html`. **In Claude Code**, `Artifact` publish with
   `url` = the ledger, `file_path` = the ledger page saved by an `Artifact` `read` of the url (no
   `path`), `root` = `<work>/publish` and `files` = those paths. Files left out stay as they are.
4. Confirm with one file listing that the new version holds each published file at its staged size
   (`wc -c <work>/publish/data/...`). If the publish failed, nothing changed: say so plainly.

## Step 1: Ask the words (one short question)

"Which list words: a mix (for example 6 phrasal verbs, 6 idioms, 3 new), or the default?"
- Default = `{"n":6,"pool":"pv","order":"spaced"}`, `{"n":6,"pool":"vocab","order":"spaced"}`,
  `{"n":3,"pool":"all","order":"new"}` (15 items).
- Map his words exactly as the vocab-session skill does: "phrasal verbs" → pool `pv`; "words",
  "idioms", "expressions", "collocations" → that type; "vocab" → `vocab`; no kind → `all`;
  "new" → `new`; "spaced repetition"/"review"/"old ones" → `spaced`; "important" → `high`;
  "mastered" → `mastered`; kind only → `random`. Mastered items stay out unless he asks.
- The total must be 12-18. If his mix adds up to more or less, say so in one line and ask
  how to adjust; don't change it yourself.
- Specific items he names are used as given (look up the exact list spelling in the two list
  files); items not on either list may still go in the passage but are not logged.

## Step 2: Ask the topic (one short question)

"Any topic or kind of text, or shall I choose?" If he leaves it to you, vary the genre
(article, essay, opinion piece, short fiction, profile, travel piece) and avoid the genres of
the last three passages (their `genre` in the reading collection). Topics can come from his
world (finance, İzmir, travel, family, technology, history), but not always.

## Step 3: Set up and pick

```bash
mkdir -p /tmp/rs && cd /tmp/rs
python3 - "<SKILL_BASE_DIR>/SKILL.md" << 'EOF'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
for name, body in re.findall(r"<!-- file: (\S+) -->\s*```(?:python)\n(.*?)```", text, re.S):
    open(name, "w", encoding="utf-8").write(body); print("wrote", name)
EOF
python3 -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null || \
  { pip install --break-system-packages -q spacy && python3 -m spacy download en_core_web_sm; }
[ -d /tmp/rs/olp ] || git clone -q --depth 1 https://github.com/openlanguageprofiles/olp-en-cefrj /tmp/rs/olp
python3 -c "import wordfreq" 2>/dev/null || pip install --break-system-packages -q wordfreq
```

If SKILL.md isn't readable from the sandbox, write the scripts from the code blocks below with
the file tool. If spaCy or the word lists can't be installed, say so plainly: the level check
can't run, so offer the passage only as "unchecked" and log nothing unless Murat agrees.

Read the ledger's files into `/tmp/rs` (see "The ledger's files"): `data/index.json`, then
`data/meta/vocab_tracker.json`, `data/meta/pv_tracker.json` and every reading file the index lists
(into `/tmp/rs/reading/`; there may be none, that's fine). Then take the baseline for the save:
`python3 ledger.py snapshot /tmp/rs`.

```bash
python3 readlog.py recent /tmp/rs/reading <DD.MM.YYYY today> 14      # items met in the last 14 days
```

Write `/tmp/rs/spec.json` with his buckets, `"reserve": 5`, and `"exclude"` = the list printed
above (so the same words don't come back within two weeks), then:

```bash
python3 pick.py meta/vocab_tracker.json meta/pv_tracker.json spec.json picked.json <DD.MM.YYYY today>
```

If it prints `SHORT:`, tell Murat in one line and ask what to do. Otherwise don't show him the
list before the passage: meeting the words fresh in the text is the point.

## Step 4: Write the passage

- 400-600 words, one title line on top. Plain prose; no bold, no highlighting, no glossary.
- Use every picked item once (inflected freely: tense, plural, pronoun objects inside a
  separable phrasal verb: "call the meeting off"). An item's list spelling may carry notes like
  "(regain consciousness)" or "someone": use the meaning shown, not the note.
- Naturalness comes first. If an item can't be used without forcing the text, swap it for a
  `reserve` item from picked.json (same kind if possible). Never drop below 12.
- Language slightly above his level: varied sentence structures (inversion, participle
  clauses, cleft sentences, advanced modals) and some C1/C2 vocabulary, but most sentences easy
  to follow at first read. It should feel like a good magazine piece, not a test.
- Never put a list word in a way that explains it ("to swirl, which means…"). Context only.

Save the text to `/tmp/rs/passage.txt` and the items actually used to `/tmp/rs/targets.json`
as `[{"key": "<list spelling>", "list": "pv" | "vocab"}, ...]`.

## Step 5: Check it

```bash
python3 readcheck.py passage.txt targets.json olp report.json
```

It checks the length, that there are 12-18 items and every one is really in the text, and the
level band. On FAIL, fix the passage (not the thresholds) and run it again: raise or lower the
harder vocabulary, add a missing item, trim or extend. Never deliver a passage that failed.

## Step 6: Give it to Murat

Send the title and the passage exactly as checked. After it, a short line: "Words from your
lists in this one:" followed by the items (list spellings, comma-separated). Then one line
inviting him to read at his own pace and say if he'd like to talk about any word or idea.
No questions about the content, no quiz.

## Step 7: Log it (right after delivering)

The chat id is in the URL `read_conversation("current")` returns; use its first 8 characters.

```bash
READING_DIR=/tmp/rs/reading python3 readlog.py doc report.json picked.json "<title>" "<genre>" "<topic>" <DD.MM.YYYY today> <chat8> doc.json
```

It prints the doc id. Stage and save it: `python3 ledger.py stage /tmp/rs reading/<doc id>=doc.json`,
then publish as "Saving" in "The ledger's files" says (one approval). If Murat says he didn't read
it after all, tell him it stays on the Reading tab for now: removing a file is done in a Claude
Code session (publish with that path set to `null` and the id taken out of `data/index.json`).

Then tell him in one line that it's on the Reading tab.

## Step 8: Optional talk

If he wants to talk about the passage, keep it natural: meanings in context, why a phrase
was used, his own examples. Flag his slips per the STANDING FEEDBACK-FOCUS RULE. His uses of
list words while talking about the passage are not unprompted uses (the naturalness check
already leaves out talk about a reading text), and the Reading tab only counts uses on later
days anyway.

## Scripts


<!-- file: pick.py -->
```python
"""Pick list words for a reading passage (or a vocab session) from Murat's two ledger lists.

Murat chooses the mix; Claude only turns his words into a spec and runs this.
Usage: python3 pick.py vocab_tracker.json pv_tracker.json spec.json picked.json [DD.MM.YYYY today]

spec.json: {"buckets": [{"n": 3, "pool": "pv", "order": "random"}, ...],
            "include_mastered": false}
  pool : pv (phrasal verbs on his study list) | vocab (all words/idioms/expressions/
         collocations) | word | idiom | expression | collocation | all (both lists)
  order: new     = never practised (practice.count 0), oldest added first
         spaced  = practised before, oldest last review first (spaced repetition)
         random  = any, random
         high    = importance High, random
         mastered= only items he marked Mastered, oldest last review first
"exclude": ["list spelling", ...] leaves those items out (reading uses it for items met in a
passage in the last 14 days). "reserve": N adds N spare items (same buckets' order) after the
picks, marked reserve, for swapping in when an item can't be woven into the text naturally.
Buckets are filled in order and never repeat an item. Mastered items are left out
unless the order is "mastered" or include_mastered is true. Items already practised
today are left out. A bucket that can't be filled is reported as SHORT, never
topped up from another pool.
"""
import json, random, sys

def dkey(d):
    if not d: return (0, 0, 0)
    dd, mm, yy = d.split(".")
    return (int(yy), int(mm), int(dd))

def load(vpath, ppath):
    v = json.load(open(vpath)); p = json.load(open(ppath))
    items = []
    for r in v["rows"]:
        pr = r.get("practice") or {}
        items.append({"key": f'v{r["id"]}', "list": "vocab", "spell": r["expr"], "type": r.get("type", "word"),
                      "importance": r.get("importance", "Medium"), "mastered": bool(r.get("mastered")),
                      "added": r.get("added"), "count": pr.get("count", 0) or 0, "last": pr.get("last")})
    for r in p["rows"]:
        L = r.get("list")
        if not L: continue
        pr = r.get("practice") or {}
        items.append({"key": f'p:{r["word"]}', "list": "pv", "spell": r["word"], "type": "phrasal verb",
                      "importance": L.get("importance", "Medium"), "mastered": bool(L.get("mastered")),
                      "added": L.get("added"), "count": pr.get("count", 0) or 0, "last": pr.get("last")})
    return items

def in_pool(it, pool):
    if pool == "all": return True
    if pool == "pv": return it["list"] == "pv"
    if pool == "vocab": return it["list"] == "vocab"
    return it["list"] == "vocab" and it["type"] == pool

def main(vpath, ppath, spec_path, out, today=None):
    spec = json.load(open(spec_path))
    rng = random.Random(spec.get("seed"))
    items = load(vpath, ppath)
    excl = {e.strip().lower() for e in spec.get("exclude", [])}
    items = [it for it in items if it["spell"].strip().lower() not in excl]
    taken, picked, short = set(), [], []
    for b in spec["buckets"]:
        n, pool, order = int(b["n"]), b.get("pool", "all"), b.get("order", "random")
        cand = [it for it in items if it["key"] not in taken and in_pool(it, pool)
                and not (today and it["last"] == today)]
        if order == "mastered":
            cand = [it for it in cand if it["mastered"]]
        elif not spec.get("include_mastered"):
            cand = [it for it in cand if not it["mastered"]]
        rng.shuffle(cand)                       # random tie-break
        if order == "new":
            cand = [it for it in cand if it["count"] == 0]
            cand.sort(key=lambda it: dkey(it["added"]))
        elif order in ("spaced", "mastered"):
            if order == "spaced": cand = [it for it in cand if it["count"] > 0]
            cand.sort(key=lambda it: dkey(it["last"]))
        elif order == "high":
            cand = [it for it in cand if it["importance"] == "High"]
        got = cand[:n]
        for it in got:
            taken.add(it["key"]); picked.append(dict(it, bucket=f'{n} {pool} {order}'))
        if len(got) < n:
            short.append(f'{n} {pool} {order}: only {len(got)} available')
    reserve = []
    if spec.get("reserve"):
        for b in spec["buckets"]:
            pool, order = b.get("pool", "all"), b.get("order", "random")
            cand = [it for it in items if it["key"] not in taken and in_pool(it, pool)
                    and not (today and it["last"] == today)
                    and (it["mastered"] if order == "mastered" else (spec.get("include_mastered") or not it["mastered"]))]
            rng.shuffle(cand)
            for it in cand:
                if len(reserve) >= int(spec["reserve"]): break
                taken.add(it["key"]); reserve.append(dict(it, bucket="reserve"))
    json.dump({"picked": picked, "reserve": reserve, "short": short}, open(out, "w"), ensure_ascii=False, indent=1)
    for i, it in enumerate(picked, 1):
        last = it["last"] or "never"
        print(f'{i:2}. {it["spell"]}  [{it["type"]}; {it["bucket"]}; practised {it["count"]}x, last {last}; {it["importance"]}]')
    for it in reserve: print(f'   reserve: {it["spell"]}  [{it["type"]}]')
    for s in short: print("SHORT:", s)
    print(f'{len(picked)} words picked')

if __name__ == "__main__":
    main(*sys.argv[1:6])
```

<!-- file: readcheck.py -->
```python
#!/usr/bin/env python3
"""
Check a reading passage before Murat sees it.

Usage: python3 readcheck.py passage.txt targets.json <cefr_dir> report.json
  passage.txt : the passage only (title on the first line is fine)
  targets.json: [{"key": "call off", "list": "pv"}, {"key": "Strike a balance", "list": "vocab"}, ...]
                (the exact list spellings from picked.json)
  cefr_dir    : clone of github.com/openlanguageprofiles/olp-en-cefrj

Checks (PASS/FAIL each, exit 1 if any fails):
  1. length 400-600 words
  2. 12-18 target items, every one of them used in the passage (lemma match, gaps allowed
     for objects and separable particles, same matcher as the naturalness check)
  3. level "slightly above Murat": share of B2+ words (B2, C1, C2 on the CEFR lists, plus
     rare off-list words) between 12% and 22% of the passage's content words, with at
     least 3% at C1/C2; and comprehension kept: at least 75% of content words at A1-B1.
     (Calibrated 28.09.26: a plain B2 text scored 1% B2+ and 99% A1-B1; a demanding
     Economist-style C1 article scored 29% B2+ and 71% A1-B1. "Slightly above" sits between.)
Also reports the level mix, the rarest words, average sentence length and MTLD, and
which targets it could not find, so Claude can fix the passage and run it again.
"""
import csv, json, os, re, sys
from collections import Counter
import spacy
try:
    from wordfreq import zipf_frequency
except ImportError:
    zipf_frequency = None

nlp = spacy.load("en_core_web_sm")
RANK = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

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
    w, l = tok.text.lower(), tok.lemma_.lower()
    for c in (l, w):
        if c in lvl: return lvl[c]
    cands = []
    if w.endswith("ily"): cands.append(w[:-3] + "y")
    if w.endswith("ly"): cands += [w[:-2], w[:-2] + "e"]
    if w.endswith("ing"): cands += [w[:-3], w[:-3] + "e"]
    if w.endswith("ed"): cands += [w[:-2], w[:-1], w[:-2] + "e"]
    if w.endswith("ness"): cands.append(w[:-4])
    for c in cands:
        if c in lvl: return lvl[c]
    return None

def est_level(word):
    """Off-list word: frequency-based guess (same bands as the naturalness check)."""
    if not zipf_frequency: return None
    z = zipf_frequency(word, "en")
    if z == 0: return None
    return "A1" if z >= 5 else "A2" if z >= 4.5 else "B1" if z >= 4 else "B2" if z >= 3.5 else "C1" if z >= 3 else "C2"

WILD = {"something", "someone", "somebody", "someone's", "somewhere", "your", "yourself",
        "you", "x", "y", "their", "his", "her", "my", "you've", "do", "doing", "it", "oneself"}
LEAD = {"to", "be", "being", "a", "an", "the"}

def expand_alts(expr):
    out = []
    for part in re.split(r"\s+/\s+", expr):
        m = re.search(r"(\S+)/(\S+)", part)
        if m:
            out += [part[:m.start()] + m.group(1) + part[m.end():], part[:m.start()] + m.group(2) + part[m.end():]]
        else:
            out.append(part)
    return out

def seqs_for(expr):
    res = []
    for alt in expand_alts(expr):
        s = re.sub(r"\([^)]*\)", " ", alt.lower())
        s = re.sub(r"\+\s*-ing", " ", s).replace("-", " ")
        toks = s.split()
        while toks and toks[0] in LEAD and len(toks) > 1: toks = toks[1:]
        if not toks: continue
        seq, gap = [], 0
        for t in nlp(" ".join(toks)):
            if t.text in WILD or t.text == "'s":
                gap = 3; continue
            if not t.is_alpha and t.text != "'t": continue
            seq.append((t.lemma_.lower(), gap if seq else 0))
            gap = 3   # room for an object inside a separable phrasal verb ("call the deal off")
        if seq: res.append(seq)
    return res

def match(seq, lemmas):
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

def mtld(tokens, ttr=0.72, min_len=10):
    def one_way(ts):
        factors, types, count = 0.0, set(), 0
        for t in ts:
            count += 1; types.add(t)
            if len(types) / count < ttr and count >= min_len:
                factors += 1; types, count = set(), 0
        if count: factors += (1 - len(types) / count) / (1 - ttr)
        return len(ts) / factors if factors else 0.0
    return (one_way(tokens) + one_way(tokens[::-1])) / 2

CONTENT = {"NOUN", "VERB", "ADJ", "ADV"}

def main(passage_path, targets_path, cefr_dir, out):
    text = open(passage_path, encoding="utf-8").read().strip()
    targets = json.load(open(targets_path, encoding="utf-8"))
    targets = targets.get("picked", targets) if isinstance(targets, dict) else targets
    lvl = load_levels(cefr_dir)
    doc = nlp(text)
    words = re.findall(r"[A-Za-z']+", text)
    sents = [s for s in doc.sents if any(t.is_alpha for t in s)]
    lemmas_by_sent = [[t.lemma_.lower() for t in s] for s in sents]

    found, missing = [], []
    for tg in targets:
        key = tg.get("key") or tg.get("spell")
        hit = None
        for seq in seqs_for(key):
            for s, lem in zip(sents, lemmas_by_sent):
                if match(seq, lem): hit = s.text.strip(); break
            if hit: break
        (found if hit else missing).append({"key": key, "list": tg.get("list"), "sentence": hit})

    counts, rare = Counter(), {}
    for t in doc:
        if not t.is_alpha or t.pos_ == "PROPN" or t.pos_ not in CONTENT: continue
        L = level_of(t, lvl)
        est = False
        if not L and len(t.text) >= 4:
            L = est_level(t.lemma_.lower()) or est_level(t.text.lower()); est = True
        if not L: continue
        counts[L] += 1
        if RANK[L] >= 5: rare[t.lemma_.lower()] = L + (" est." if est else "")
    total = sum(counts.values()) or 1
    pct = {k: round(counts[k] / total * 100, 1) for k in RANK}
    b2plus = round(pct["B2"] + pct["C1"] + pct["C2"], 1)
    c1plus = round(pct["C1"] + pct["C2"], 1)
    easy = round(pct["A1"] + pct["A2"] + pct["B1"], 1)
    n_words = len(words)
    avg_sent = round(n_words / max(len(sents), 1), 1)
    md = round(mtld([w.lower() for w in words]), 1) if n_words >= 100 else None

    checks = [
        ("length 400-600 words", 400 <= n_words <= 600, f"{n_words} words"),
        ("12-18 target items", 12 <= len(targets) <= 18, f"{len(targets)} targets"),
        ("every target used", not missing, "missing: " + ", ".join(m["key"] for m in missing)),
        ("B2+ share 12-22% of content words", 12 <= b2plus <= 22, f"{b2plus}%"),
        ("C1/C2 at least 3%", c1plus >= 3, f"{c1plus}%"),
        ("A1-B1 at least 75% (comprehension)", easy >= 75, f"{easy}%"),
    ]
    for name, ok, detail in checks:
        print(("PASS: " if ok else "FAIL: ") + name + f"  ({detail})")
    ok_all = all(ok for _, ok, _ in checks)
    report = {"words": n_words, "sentences": len(sents), "avg_sentence_len": avg_sent, "mtld": md,
              "levels": pct, "b2plus_share": b2plus, "c1plus_share": c1plus, "easy_share": easy,
              "targets_found": found, "targets_missing": missing,
              "rare_words": dict(sorted(rare.items())), "passed": ok_all}
    json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"levels: " + " ".join(f"{k} {v}%" for k, v in pct.items()) +
          f" · avg sentence {avg_sent} words · MTLD {md}")
    print("C1/C2 words: " + ", ".join(f"{w} ({l})" for w, l in sorted(rare.items())))
    for f in found: print(f"  found  {f['key']}: {f['sentence'][:110]}")
    for m in missing: print(f"  MISSING {m['key']}")
    print("ALL CHECKS PASSED" if ok_all else "CHECKS FAILED")
    if not ok_all: raise SystemExit(1)

if __name__ == "__main__":
    main(*sys.argv[1:5])
```

<!-- file: readlog.py -->
```python
#!/usr/bin/env python3
"""
Reading log helpers for Murat's Fluency Ledger (`reading` collection).

1) Items met in recent passages (to leave out of the next pick):
   python3 readlog.py recent <reading_dir> <DD.MM.YYYY today> [days=14]
   reading_dir: the folder the ledger's `data/reading/` files were moved into
   (for example /tmp/rs/reading). Prints a JSON list of list spellings; missing folder = [].

2) Build the reading document after readcheck.py has PASSED:
   python3 readlog.py doc report.json picked.json "<title>" "<genre>" "<topic>" <DD.MM.YYYY> <chat8> out.json
   picked.json: pick.py output; only the items readcheck found are logged (spare items that
   were not used are left out). Prints the doc id: r_<YYYYMMDD>_<chat8>, with _2, _3 ... if
   <reading_dir>/<id>.json already exists for a second passage in the same chat (pass the
   reading_dir as READING_DIR env var to check).

The document: {date, title, genre, topic, words, b2plus_share, c1plus_share, easy_share,
avg_sentence_len, items: [{key, list}], chat}. Reading never counts as a use or a review:
this log is kept apart from the trackers on purpose.
"""
import json, os, sys, glob
from datetime import datetime, timedelta

def d(s): return datetime.strptime(s, "%d.%m.%Y")

def recent(reading_dir, today, days="14"):
    out = set()
    if os.path.isdir(reading_dir):
        cutoff = d(today) - timedelta(days=int(days))
        for f in glob.glob(os.path.join(reading_dir, "*.json")):
            doc = json.load(open(f, encoding="utf-8")); doc = doc.get("data", doc)
            if doc.get("date") and d(doc["date"]) >= cutoff:
                for it in doc.get("items", []): out.add(it["key"])
    print(json.dumps(sorted(out), ensure_ascii=False))

def build(report, picked, title, genre, topic, date, chat8, out):
    rep = json.load(open(report, encoding="utf-8"))
    if not rep.get("passed"):
        raise SystemExit("readcheck.py did not pass; fix the passage first")
    pk = json.load(open(picked, encoding="utf-8"))
    pool = (pk.get("picked", []) + pk.get("reserve", [])) if isinstance(pk, dict) else pk
    lst = {(p.get("spell") or p.get("key")).lower(): p.get("list") for p in pool}
    items = []
    for f in rep["targets_found"]:
        items.append({"key": f["key"], "list": f.get("list") or lst.get(f["key"].lower(), "vocab")})
    base = f"r_{d(date).strftime('%Y%m%d')}_{chat8}"
    rid, n, rdir = base, 1, os.environ.get("READING_DIR", "")
    while rdir and os.path.exists(os.path.join(rdir, rid + ".json")):
        n += 1; rid = f"{base}_{n}"
    doc = {"date": date, "title": title, "genre": genre, "topic": topic, "words": rep["words"],
           "b2plus_share": rep["b2plus_share"], "c1plus_share": rep["c1plus_share"],
           "easy_share": rep["easy_share"], "avg_sentence_len": rep["avg_sentence_len"],
           "items": items, "chat": chat8}
    json.dump(doc, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(rid)
    print(f"{len(items)} list items logged: " + ", ".join(i["key"] for i in items))

if __name__ == "__main__":
    if sys.argv[1] == "recent": recent(*sys.argv[2:5])
    elif sys.argv[1] == "doc": build(*sys.argv[2:10])
    else: raise SystemExit(__doc__)
```

<!-- file: ledger.py -->
```python
"""Save guard for Murat's Fluency Ledger (since 30.10.26).

The ledger's data lives in published files inside the ledger artifact (data/index.json,
data/meta/<name>.json, data/sessions/<id>.json, data/reading/<id>.json). A skill reads the files
it needs into a work folder at the same paths without "data/" (e.g. /tmp/nc/meta/pv_tracker.json),
and saves by publishing only the files that changed. This script makes that save safe.

  python3 ledger.py snapshot <workdir>
      Run right after reading. Copies what was read (index.json, meta/, sessions/, reading/)
      to <workdir>/_before/, the baseline every later check compares with, and prints the counts.

  python3 ledger.py stage <workdir> [--session <doc_id>] <target>=<file>[:merge][?] ...
      <target> is a ledger path without "data/" and ".json": meta/pv_tracker, sessions/<id>,
      reading/<id>. ":merge" lays the file's top-level fields over the read copy (for files that
      hold only the changed fields, like vocab-session's rows files). A trailing "?" marks a file
      that a step writes only sometimes: it is skipped when it doesn't exist. --session names the session
      being saved, so a rerun of the same chat may take back the prep_watch rows it added itself.
      Checks every file, refuses the whole save if any list would lose a row (or a row would lose
      a date or a review), adds new session/reading ids to index.json, and writes the files to
      publish under <workdir>/publish/data/. Prints "PUBLISH: ..." with the paths to publish, or
      "REFUSED: ..." (exit 1, nothing staged).
"""
import json, os, shutil, sys

PARTS = ("index.json", "meta", "sessions", "reading")
# list field, row key ("dict" = a keyed object): a save may never drop a row or a key
RULES = {
    "meta/pv_tracker": ("rows", "word"), "meta/vocab_tracker": ("rows", "id"),
    "meta/prep_watch": ("rows", "word"), "meta/interference": ("patterns", "key"),
    "meta/chunks": ("items", "id"), "meta/phave": ("items", "word"),
    "meta/vocab_items": ("items", "id"), "meta/lexicon": ("words", "dict"),
    "meta/registry": ("concepts", "dict"),
}
GROWING = {"meta/pv_tracker", "meta/vocab_tracker"}   # rows whose dates and reviews only ever grow


def load(p):
    d = json.load(open(p))
    return d.get("data", d) if isinstance(d, dict) and set(d) <= {"data", "version", "id"} else d


def snapshot(wd):
    b = os.path.join(wd, "_before")
    shutil.rmtree(b, ignore_errors=True); os.makedirs(b)
    if not os.path.exists(os.path.join(wd, "index.json")):
        sys.exit("REFUSED: index.json is missing. Read data/index.json first.")
    for p in PARTS:
        s = os.path.join(wd, p)
        if os.path.isdir(s): shutil.copytree(s, os.path.join(b, p))
        elif os.path.exists(s): shutil.copy(s, os.path.join(b, p))
    print("SNAPSHOT:", ", ".join(f"{t} {len(load(os.path.join(b, t + '.json'))[f])}"
                                 for t, (f, _) in RULES.items() if os.path.exists(os.path.join(b, t + ".json"))))


def keys(doc, field, key):
    v = doc.get(field)
    if key == "dict":
        if not isinstance(v, dict): raise ValueError(f"'{field}' is not an object")
        return {k: None for k in v}
    if not isinstance(v, list): raise ValueError(f"'{field}' is not a list")
    out = {}
    for r in v:
        k = r.get(key) if isinstance(r, dict) else None
        if k is None: raise ValueError(f"a row in '{field}' has no '{key}'")
        out[k] = r
    return out


def check(target, old, new, session, problems, lines):
    if not isinstance(new, dict): problems.append(f"{target}: not a JSON object"); return
    if target.startswith("sessions/") and not new.get("date"): problems.append(f"{target}: no 'date'")
    if target not in RULES or old is None: return
    field, key = RULES[target]
    try: o, n = keys(old, field, key), keys(new, field, key)
    except ValueError as e: problems.append(f"{target}: {e}"); return
    gone = [k for k in o if k not in n
            and not (target == "meta/prep_watch" and session and o[k].get("added") == session)]
    if gone: problems.append(f"{target}: {len(gone)} row(s) would be lost: {', '.join(map(str, gone[:8]))}")
    if target in GROWING:
        for k, r in o.items():
            m = n.get(k)
            if not m: continue
            if len(m.get("dates") or []) < len(r.get("dates") or []):
                problems.append(f"{target}: '{k}' would lose dates ({len(r['dates'])} -> {len(m.get('dates') or [])})")
            if ((m.get("practice") or {}).get("count") or 0) < ((r.get("practice") or {}).get("count") or 0):
                problems.append(f"{target}: '{k}' would lose reviews")
    lines.append(f"  {target} {field}: {len(o)} -> {len(n)}")


def stage(wd, args):
    session = None
    if "--session" in args:
        i = args.index("--session"); session = args[i + 1]; del args[i:i + 2]
    b = os.path.join(wd, "_before")
    if not os.path.exists(os.path.join(b, "index.json")):
        sys.exit("REFUSED: no snapshot. Run 'ledger.py snapshot' right after reading the files.")
    idx = load(os.path.join(b, "index.json")); idx0 = json.loads(json.dumps(idx))
    out_root = os.path.join(wd, "publish"); shutil.rmtree(out_root, ignore_errors=True)
    problems, lines, staged = [], [], {}
    for a in args:
        target, _, src = a.partition("=")
        optional = src.endswith("?"); src = src[:-1] if optional else src
        if optional and not os.path.exists(os.path.join(wd, src)): continue
        merge = src.endswith(":merge"); src = src[:-6] if merge else src
        target = target.strip().removeprefix("data/").removesuffix(".json")
        col = target.split("/")[0]
        if col not in ("meta", "sessions", "reading") or target.count("/") != 1:
            problems.append(f"{target}: not a ledger path (meta/<name>, sessions/<id>, reading/<id>)"); continue
        bp = os.path.join(b, target + ".json")
        old = load(bp) if os.path.exists(bp) else None
        if old is None and col == "meta" and target.split("/")[1] in idx.get("meta", []):
            problems.append(f"{target}: exists in the ledger but wasn't read; read it first"); continue
        if old is None and col == "sessions" and target.split("/")[1] in idx.get("sessions", []):
            problems.append(f"{target}: this session is already saved but wasn't read; read it first"); continue
        try: new = load(os.path.join(wd, src) if not os.path.isabs(src) else src)
        except Exception as e: problems.append(f"{target}: can't read {src} ({e})"); continue
        if merge:
            if old is None: problems.append(f"{target}: ':merge' needs the read copy"); continue
            new = {**old, **new}
        check(target, old, new, session, problems, lines)
        staged[target] = new
        ids = idx.setdefault(col, [])
        if target.split("/")[1] not in ids: ids.append(target.split("/")[1]); ids.sort()
    for col, ids in idx0.items():
        if isinstance(ids, list) and not set(ids) <= set(idx.get(col, [])): problems.append(f"index.json: {col} would lose ids")
    if not staged: problems.append("nothing to save")
    if problems:
        print("REFUSED: nothing was staged. Fix these, or tell Murat if a list really would shrink:")
        for p in problems: print("  - " + p)
        sys.exit(1)
    for target, doc in staged.items():
        p = os.path.join(out_root, "data", target + ".json"); os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(doc, open(p, "w"), ensure_ascii=False)
    paths = [f"data/{t}.json" for t in staged]
    if idx != idx0:
        json.dump(idx, open(os.path.join(out_root, "data", "index.json"), "w"), ensure_ascii=False, indent=1)
        paths.append("data/index.json")
    print("CHECKS PASSED (no list loses a row):"); print("\n".join(lines) if lines else "  (no tracker lists in this save)")
    print(f"PUBLISH: {len(paths)} file(s) from {out_root}: " + " ".join(paths))


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("snapshot", "stage"): sys.exit(__doc__)
    snapshot(sys.argv[2]) if sys.argv[1] == "snapshot" else stage(sys.argv[2], sys.argv[3:])
```
