---
name: "vocab-session"
description: "Run Murat's vocabulary practice session: he picks Mode (a) story only or Mode (b) quiz page + stories, and the word mix; Claude picks the words from his Fluency Ledger lists, builds and checks the quiz, drives the story loop and records the reviews. Trigger on \"vocabulary session\", \"vocab session\" or \"let's practice vocabulary\" in My English Journey."
---

# Vocab Session

Runs when Murat says "vocabulary session", "vocab session" or "let's practice vocabulary".
It replaces the step-by-step part of Project Instructions Section 4 (built 28.09.26).

Murat's study list lives in the Fluency Ledger (https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK),
in two lists:
- `meta/pv_tracker`: phrasal verbs (prepositional verbs like "dwell on" count as phrasal verbs).
  Rows with a `list` block are on his study list. Spelled in base form (`word`, e.g. "catch up with").
- `meta/vocab_tracker`: words, collocations, expressions and idioms (`expr`, `type`).
Each item has `practice: {count, last}` (vocab-session reviews) and `mastered` (his own label).

Standing rules, from Murat:
- **Murat chooses the mode and the mix. Claude never chooses them for him.** Claude only turns his
  words into a pick and runs it.
- Only Murat adds items to the lists. Words from a fresh source he gives in the session are
  practised but never added.
- Practice counts as a review (`practice`), never as an unprompted use (`dates`). Never change
  `dates`, `mastered`, or anything else on a row.
- Ask one question at a time.
- In voice mode keep every turn short: no recaps of earlier turns (Section 0 of the Project
  Instructions).

**The drill marks (Murat, 29.10.26).** The story loop is the drill, and it is wrapped in two fixed
marks, said exactly like this, each at the very start of Claude's message:
- **"Vocab drill starts."** in the message that gives the first story word;
- **"Vocab drill ends."** in the message after the last story, or after Murat says in any words
  that he wants to stop ("let's finish", "that's enough").
Never close the drill on a guess. If he drifts into free conversation without saying the drill is
over, ask once: "Shall we close the vocab drill?" Only these marks count; the fixing slot has its own
("Fixing slot starts" / "Fixing slot ends"), and the two are never mixed. If the drill stops and starts
again later in the chat, use a new pair of marks each time.
The naturalness check keeps the practised words out **only between the marks**: there they are
practice (a review). A practised word that Murat uses on his own outside the marks, before or after
the drill, is a real come-up. The quiz page (Mode b) is outside the chat, so it needs no marks.

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

## Step 1: Ask the mode (always first, every session)

One short question:
- **(a) Light**: story only. Claude says a word, Murat tells a story with it. No quiz.
- **(b) Full**: a quiz page with all 11 exercise formats, then the same story loop.

## Step 2: Ask the words

One short question: which words? Murat can answer in any of these ways, or mix them:
- a mix from his lists, e.g. "3 phrasal verbs, 3 new, 4 spaced repetition";
- specific items he names;
- a fresh source (a pasted list, a transcript, a PDF from his tutor). Use only words from that
  source; they don't need to be on his lists.

If his answer is unclear (for example "10 words" with no kind), ask once what mix he wants.
Don't fill in a mix yourself.

### Picking from the lists

Set up the scripts (see "Scripts" at the bottom):

```bash
mkdir -p /tmp/vs && cd /tmp/vs
python3 - "<SKILL_BASE_DIR>/SKILL.md" << 'EOF'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
for name, body in re.findall(r"<!-- file: (\S+) -->\s*```(?:python)\n(.*?)```", text, re.S):
    open(name, "w", encoding="utf-8").write(body); print("wrote", name)
EOF
```

If SKILL.md isn't readable from the sandbox, write the scripts from the code blocks below with the
file tool instead.

Read both lists into `/tmp/vs` (see "The ledger's files"): `data/index.json`, then
`data/meta/vocab_tracker.json` and `data/meta/pv_tracker.json`. Then take the baseline Step 5's save
is checked against: `python3 ledger.py snapshot /tmp/vs`.

Turn Murat's mix into `/tmp/vs/spec.json`, one bucket per part of the mix, in the order he said it:

```json
{"buckets": [{"n": 3, "pool": "pv", "order": "random"},
             {"n": 3, "pool": "all", "order": "new"},
             {"n": 4, "pool": "all", "order": "spaced"}],
 "include_mastered": false}
```

How his words map:
- "phrasal verbs" → pool `pv`. "words" → `word`; "idioms" → `idiom`; "expressions" →
  `expression`; "collocations" → `collocation`; "vocab" / "vocab list" (no phrasal verbs) →
  `vocab`. No kind named ("3 new") → `all`.
- "new" → order `new` (never practised). "spaced repetition" / "review" / "old ones" → `spaced`
  (practised before, oldest last review first). "high priority" / "important" → `high`.
  "mastered" → `mastered`. Kind only ("3 phrasal verbs") → `random`.
- Kind and order combine: "3 new phrasal verbs" → `{"n":3,"pool":"pv","order":"new"}`.
- Mastered items are left out unless he asks for them ("include mastered" → `include_mastered: true`).

```bash
python3 pick.py meta/vocab_tracker.json meta/pv_tracker.json spec.json picked.json <DD.MM.YYYY today>
```

It never repeats an item across buckets and never tops up a short bucket from another pool. If it
prints `SHORT:`, tell Murat in one line (e.g. "Only 2 new idioms left") and ask what to do.
Show him the picked list in one short message (the words only) and let him swap any before
starting. The spellings in `picked.json` are the exact list spellings; keep them for Step 5.

When Murat names specific items, look each one up in the two list files (case-insensitive; for a
phrasal verb, its base-form `word`) and use the exact list spelling from then on. If one isn't on
either list, treat it as a fresh-source word (practised, not recorded) and tell him in one line,
since he may want to add it himself.

## Step 3a: Mode (a), story only

1. Say ONE target word or expression, nothing else (no quiz, no example sentence). The message
   with the first word starts with "Vocab drill starts."
2. Murat tells a story with it.
3. Reply in one or two short sentences: if he used the word naturally, say so briefly; if not,
   give the natural version ("Natives would say …"). Then give the next word.
4. Repeat until every word has a story, or until Murat stops ("quit at peak" is fine).
   Natural conversation and topic shifts along the way are valid practice.
5. Close with "Vocab drill ends." at the start of the next message (see "The drill marks").

Keep track of which words actually got a story; only those are recorded in Step 5.

## Step 3b: Mode (b), quiz page, then stories

### Write the content

Write `/tmp/vs/content.json` for the picked words (schema at the top of build.py). Rules:
- One item per word in EVERY exercise (all 11), whatever the number of words. Never cut formats
  unless Murat asks for a shorter version that day.
- `target` = the exact list spelling. `meaning` = a short plain phrase (under 12 words).
- Exactly one `___` gap per fill sentence and per Exercise 4/11 sentence. For a separable phrasal
  verb, gap the whole phrase and put the object inside the answer ("That flight ___." →
  "knocked me out"). List accepted variants in `answers` (tense forms, with/without "it").
- Never put the target word in a sentence where it is the answer.
- Exercises 2 and 7 (meaning MC): write the prompt so any meaning can complete it, e.g.
  "In 'we had to sort through the files', sort through means…". The script fills the options
  with the meanings of today's other words.
- Exercises 4 and 11: write a sentence with one `___`; the script fills the options with
  today's other words. Make sure only the target fits.
- Exercise 3: a word bank of the forms used, one item per word.
- Exercise 5: the missing part of a collocation or phrasal verb ("sort ___", "a ___ schedule").
- Exercise 6: pick one theme from Murat's life (work, İzmir, family, travel) and use it for all items.
- Exercise 8: a realistic mistake a Turkish speaker might make with the word; `answer` = the
  corrected sentence; `hint` explains the rule without giving the corrected sentence.
- Exercise 9: the gap is exactly one word.
- Exercise 10: "A: … / B: … ___" mini dialogues.
- Use Murat's real world for contexts where it fits (finance work, İzmir, his daughter, travel).

### Build and check

```bash
python3 build.py content.json quiz.html
python3 pagetest.py quiz.html
```

build.py checks: all 11 formats; every word in every exercise; a different item order in every
exercise (no word in the same slot twice in a row, no word keeps opening the exercises); correct
answers spread across A/B/C in Exercises 2, 4, 7 and 11; wrong options only from today's words;
answers hidden and one gap per sentence; hints never giving the answer away. pagetest.py opens the
page in Chromium and clicks through it (right/wrong answers, hints, Progress view, phone width).

Fix content.json and rebuild until both print PASSED. Never deliver a page that failed a check.
If Chromium can't run here, say so and deliver only after build.py passes.

### Deliver

Publish it to the fixed quiz page, updated in place every session:
https://claude.ai/artifact/PkXEna9VTLyi2FDj4LDtD9 . In a chat: read that artifact first
(`read_artifact`), then `publish_files` to it with `/tmp/vs/quiz.html` as its page (`index.html`).
In Claude Code: `Artifact` `read` on that url, then `Artifact` publish with
`file_path: /tmp/vs/quiz.html` and `url` set to it (no `icon`). If neither works, send quiz.html as
a file instead.

Tell Murat in one line that the quiz is ready and to say "done" when he has finished. Claude can't
see what he does on the page, so wait for his signal.

### Stories

When he says he's done, run the story loop exactly as in Mode (a), over the same words, with the
same marks ("Vocab drill starts." / "Vocab drill ends.") around the stories. This part is not optional.

## Step 4: Critical rules (both modes)

1. Only words from the chosen source. Never add a word that isn't on the list or in his source.
2. Never present the same question twice in a session (the same word in different formats is fine).
3. Never show the target word in its own question or item header.
4. Accept negative forms, variants and related expressions when the core meaning is right.
5. Murat can stop at any point. Record what was practised so far.

## Step 5: Record the reviews

At the end (all stories done, or Murat stops), write the words that were practised (quiz done
and/or a story told) to `/tmp/vs/practised.txt`, one per line, in their exact list spelling.
Include fresh-source words too; the script skips them.

```bash
python3 record.py meta/vocab_tracker.json meta/pv_tracker.json practised.txt <DD.MM.YYYY today>
```

It adds one review per word (+1 `practice.count`, `practice.last` = today), at most once per day,
the same rule the naturalness check uses, so a later check the same day can't count them twice.
Then save the changed list(s) named on its `WRITE:` line in ONE publish, so Murat approves once.
Stage only the lists named there:
`python3 ledger.py stage /tmp/vs meta/vocab_tracker=vocab_rows.json:merge meta/pv_tracker=pv_rows.json:merge`
(drop the pair for a list `WRITE:` doesn't name), then publish as "Saving" in "The ledger's files"
says. On `REFUSED`, nothing is saved: tell Murat what it lists. Never split this into two
publishes. If `WRITE:` names no list, don't save anything. If the ledger's version changed before
publishing, nothing was saved: read both lists again, take a new snapshot, rerun record.py on the
fresh files, stage and publish again. (A word already recorded today is skipped, so a rerun never
counts twice.)

Finish with one short message:
- "Recorded N reviews: …" (the words), plus any word that wasn't on either list.
- A line **Practised words:** listing every word practised this session (list and fresh-source
  words). The naturalness check reads this line together with the drill marks: uses of these
  words between "Vocab drill starts." and "Vocab drill ends." count as practice; uses outside the
  marks count as unprompted come-ups.

## Scripts


<!-- file: pick.py -->
```python
"""Pick the words for a vocab session from Murat's two ledger lists.

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
    json.dump({"picked": picked, "short": short}, open(out, "w"), ensure_ascii=False, indent=1)
    for i, it in enumerate(picked, 1):
        last = it["last"] or "never"
        print(f'{i:2}. {it["spell"]}  [{it["type"]}; {it["bucket"]}; practised {it["count"]}x, last {last}; {it["importance"]}]')
    for s in short: print("SHORT:", s)
    print(f'{len(picked)} words picked')

if __name__ == "__main__":
    main(*sys.argv[1:6])
```

<!-- file: build.py -->
```python
"""Build Murat's Mode (b) vocab quiz page and check every rule before delivery.

Usage: python3 build.py content.json quiz.html [seed]

Claude writes content.json (the sentences); this script does the parts that must never be
left to judgement: all 11 formats, one item per word in every exercise, wrong multiple-choice
options taken only from the same word set, correct answers spread across A/B/C, a different
item order in every exercise, hidden answers, and hints that never give the answer away.
It prints PASS/FAIL for each rule and exits with an error if anything fails.

content.json:
{
 "title": "Vocabulary Practice", "subtitle": "10 words · 28 Sept",
 "words": [{"target": "give up", "meaning": "stop trying"}, ...],      # target = exact list spelling
 "ex": {
  "1":  [{"target", "prompt" (with ___), "answers": [..]}],            # plain sentences
  "2":  [{"target", "prompt"}],        # "In 'she gave up', give up means..." -> options = meanings (auto)
  "3":  {"bank": "gave up / looked after / ...", "items": [{"target", "prompt", "answers"}]},  # correct form
  "4":  [{"target", "prompt"}],        # sentence with ___ -> options = targets (auto)
  "5":  [{"target", "prompt", "answers"}],   # collocation / missing part only ("give ___")
  "6":  {"theme": "Workplace Behaviour", "items": [{"target", "prompt", "answers"}]},  # thematic fill
  "7":  [{"target", "prompt"}],        # second definition MC, new context -> options = meanings (auto)
  "8":  [{"target", "prompt" (a wrong sentence), "answer" (the corrected sentence), "hint"}],
  "9":  [{"target", "prompt", "answers"}],   # ONE word gap
  "10": [{"target", "prompt" ("A: ... / B: ... ___"), "answers"}],  # mini dialogue
  "11": [{"target", "prompt"}]         # best phrase in context -> options = targets (auto)
 }
}
"""
import json, random, re, sys

FORMATS = {
    1: ("Complete the sentences", "fill", "Plain sentence blanks, no word bank."),
    2: ("Choose the correct meaning", "mc", "Pick the meaning that fits."),
    3: ("Complete with the correct form", "fill", None),
    4: ("Choose the correct word", "mc", "Every option is one of today's words. Which one fits?"),
    5: ("Complete the collocations", "fill", "Write the missing part only."),
    6: (None, "fill", "Same words, one theme."),
    7: ("Multiple choice", "mc", "Meanings again, new contexts."),
    8: ("Find the mistake", "reveal", "Write the corrected sentence, then reveal and grade yourself."),
    9: ("Complete with ONE word", "fill", "Exactly one word goes in each gap."),
    10: ("Mini dialogue completion", "fill", "Complete each dialogue."),
    11: ("Choose the best phrase", "mc", "Every option is one of today's words."),
}
DEF_MC, WORD_MC = (2, 7), (4, 11)

def norm(s): return re.sub(r"\s+", " ", (s or "").strip().lower())

def orders(n, k, rng, tries=20000):
    """k permutations of range(n): consecutive exercises never put a word in the same slot,
    and no word opens more exercises than it has to."""
    if n == 1: return [[0]] * k
    cap = -(-k // n)
    for _ in range(tries):
        out, firsts, ok = [], {}, True
        for e in range(k):
            for _ in range(500):
                p = list(range(n)); rng.shuffle(p)
                if e and any(a == b for a, b in zip(p, out[-1])): continue
                if firsts.get(p[0], 0) >= cap: continue
                break
            else:
                ok = False; break
            out.append(p); firsts[p[0]] = firsts.get(p[0], 0) + 1
        if ok: return out
    raise SystemExit("could not find item orders")

def main(content_path, out_path, seed=None):
    rng = random.Random(seed)
    c = json.load(open(content_path))
    words = c["words"]; targets = [w["target"] for w in words]
    meaning = {w["target"]: w["meaning"] for w in words}
    n = len(targets); fails = []
    if n < 2: raise SystemExit("need at least 2 words")
    n_opt = min(3, n)

    raw = {}
    for i in range(1, 12):
        v = c["ex"].get(str(i))
        if v is None: fails.append(f"exercise {i} missing"); raw[i] = []; continue
        raw[i] = v["items"] if isinstance(v, dict) else v
        got = sorted(norm(it["target"]) for it in raw[i])
        if got != sorted(norm(t) for t in targets):
            fails.append(f"exercise {i}: needs exactly one item per word (has {[it['target'] for it in raw[i]]})")
        for it in raw[i]:
            if it["target"] not in meaning: fails.append(f"exercise {i}: unknown target {it['target']!r}")
    if fails:
        for f in fails: print("FAIL:", f)
        raise SystemExit(1)

    perms = orders(n, 11, rng)
    # correct-answer letters for the 4 MC exercises: as even as possible
    positions = {}
    for e in DEF_MC + WORD_MC:
        pos = [j % n_opt for j in range(n)]; rng.shuffle(pos); positions[e] = pos

    exercises = []
    for e in range(1, 12):
        title, typ, note = FORMATS[e]
        v = c["ex"][str(e)]
        if e == 3: note = "Word bank: " + v["bank"]
        if e == 6: title = v["theme"]
        by_t = {norm(it["target"]): it for it in raw[e]}
        items = []
        for slot, ti in enumerate(perms[e - 1]):
            t = targets[ti]; it = by_t[norm(t)]
            if typ == "fill":
                items.append({"prompt": it["prompt"], "answers": it["answers"], "target": t,
                              "meaning": it.get("meaning") or meaning[t]})
            elif typ == "reveal":
                items.append({"prompt": it["prompt"], "answer": it["answer"], "target": t, "hint": it["hint"]})
            else:
                others = [x for x in targets if x != t]; rng.shuffle(others)
                pool = others[:n_opt - 1]
                if e in DEF_MC:
                    right, wrong = meaning[t], [meaning[x] for x in pool]
                    hint_meaning = None            # the meaning IS the answer here: no meaning hint
                else:
                    right, wrong = t, pool
                    hint_meaning = meaning[t]
                k = positions[e][slot]
                opts = wrong[:]; opts.insert(k, right)
                items.append({"prompt": it["prompt"], "options": opts, "correct": k, "target": t,
                              "meaning": hint_meaning, "_pool": pool})
        exercises.append({"id": e, "title": f"Exercise {e} — {title}", "type": typ, "note": note, "items": items})

    # ---------- checks ----------
    checks = []
    def check(name, ok, detail=""):
        checks.append((name, ok)); print(("PASS: " if ok else "FAIL: ") + name + (f"  ({detail})" if detail and not ok else ""))

    check("all 11 formats present", [x["id"] for x in exercises] == list(range(1, 12)))
    check("every word in every exercise", all(sorted(norm(i["target"]) for i in x["items"]) ==
                                               sorted(norm(t) for t in targets) for x in exercises))
    seq = [[i["target"] for i in x["items"]] for x in exercises]
    same = [(a + 1) for a in range(10) if any(p == q for p, q in zip(seq[a], seq[a + 1]))]
    check("item order changes every exercise (no word in the same slot twice in a row)", not same, f"exercises {same}")
    firsts = {}
    for s in seq: firsts[s[0]] = firsts.get(s[0], 0) + 1
    check("no word keeps opening the exercises", max(firsts.values()) <= -(-11 // n), str(firsts))
    letters = {}
    for x in exercises:
        if x["type"] != "mc": continue
        cnt = [0] * n_opt
        for i in x["items"]: cnt[i["correct"]] += 1
        letters[x["id"]] = cnt
    check("correct answers spread across A/B/C in exercises 2, 4, 7, 11",
          all(max(v) - min(v) <= 1 for v in letters.values()), str(letters))
    bad = []
    for x in exercises:
        if x["type"] != "mc": continue
        for i in x["items"]:
            if any(p not in targets for p in i["_pool"]) or i["target"] in i["_pool"]:
                bad.append((x["id"], i["target"]))
            if len(set(i["options"])) != len(i["options"]): bad.append((x["id"], i["target"], "duplicate option"))
    check("wrong options come only from the same word set", not bad, str(bad))
    leak = []
    for x in exercises:
        for i in x["items"]:
            p = norm(i["prompt"])
            if x["type"] == "fill":
                if i["prompt"].count("___") != 1: leak.append((x["id"], i["target"], "needs exactly one ___ gap"))
                for a in i["answers"]:
                    if re.search(r"(?<![a-z])" + re.escape(norm(a)) + r"(?![a-z])", p.replace("___", " ")):
                        leak.append((x["id"], i["target"], "answer in prompt"))
            if x["id"] in WORD_MC and norm(i["target"]) in p: leak.append((x["id"], i["target"], "target in prompt"))
            if x["id"] in WORD_MC and i["prompt"].count("___") != 1: leak.append((x["id"], i["target"], "needs exactly one ___ gap"))
    check("answers hidden, exactly one gap per sentence", not leak, str(leak))
    hint_leak = []
    for x in exercises:
        for i in x["items"]:
            if x["type"] == "mc" and i["meaning"] and norm(i["meaning"]) in [norm(o) for o in i["options"]]:
                hint_leak.append((x["id"], i["target"]))
            if x["type"] == "reveal" and norm(i["answer"]) in norm(i["hint"]): hint_leak.append((x["id"], i["target"]))
    check("hints never give the answer away", not hint_leak, str(hint_leak))

    for x in exercises:
        for i in x["items"]: i.pop("_pool", None)
    html = PAGE.replace("__TITLE__", esc(c.get("title", "Vocabulary Practice"))) \
               .replace("__SUBTITLE__", esc(c.get("subtitle", ""))) \
               .replace("__EXERCISES__", json.dumps(exercises, ensure_ascii=False, indent=1))
    open(out_path, "w").write(html)
    json.dump(exercises, open(out_path + ".data.json", "w"), ensure_ascii=False, indent=1)
    ok = all(o for _, o in checks)
    print(("ALL CHECKS PASSED" if ok else "CHECKS FAILED") + f": {n} words x 11 exercises = {n * 11} items -> {out_path}")
    if not ok: raise SystemExit(1)

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

PAGE = r"""<title>Vocab Practice Quiz</title>
<style>
  :root{--bg:#f6f7fb;--card:#ffffff;--border:#e7e9f2;--text:#232842;--text-dim:#6b7290;--text-faint:#9498b0;--accent:#6d5cf6;--accent-soft:#efecff;--mint:#1fb383;--mint-soft:#e4f8f0;--coral:#f2554c;--coral-soft:#fdeceb;--gold:#e69a1f;--gold-soft:#fdf3e2;}
  *{box-sizing:border-box;}
  body{margin:0;color-scheme:light;background:radial-gradient(circle at 10% -5%, #efeaff 0%, transparent 45%),radial-gradient(circle at 95% 10%, #e2f9f0 0%, transparent 40%),var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,sans-serif;min-height:100vh;padding:32px 16px 60px;}
  .wrap{max-width:780px;margin:0 auto;}
  .top{text-align:center;margin-bottom:22px;}
  .top .eyebrow{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:8px;}
  .top h1{font-size:27px;font-weight:800;margin:0 0 6px;letter-spacing:-0.01em;color:#191d33;}
  .top p{font-size:13.5px;color:var(--text-dim);margin:0;}
  .mode-switch{display:flex;justify-content:center;gap:8px;margin:18px 0 20px;}
  .mode-btn{font-size:12.5px;font-weight:700;padding:8px 16px;border-radius:99px;border:1px solid var(--border);background:var(--card);color:var(--text-dim);cursor:pointer;}
  .mode-btn.active{background:var(--accent);color:#fff;border-color:var(--accent);}
  .progress-track{height:7px;background:var(--card);border-radius:99px;margin:0 0 20px;overflow:hidden;border:1px solid var(--border);}
  .progress-fill{height:100%;background:linear-gradient(90deg,var(--accent),var(--mint));border-radius:99px;transition:width .3s ease;}
  .tabs{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:18px;}
  .tab{font-size:12.5px;font-weight:700;border:1px solid var(--border);background:var(--card);color:var(--text-dim);padding:7px 13px;border-radius:9px;cursor:pointer;transition:all .15s ease;}
  .tab:hover{border-color:var(--accent);color:var(--accent);}
  .tab.active{background:var(--accent-soft);color:var(--accent);border-color:var(--accent);}
  .tab.done{color:var(--mint);}
  .tab.done::after{content:" ✓";}
  .tab.active.done{color:var(--accent);}
  .card{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:24px 24px 20px;box-shadow:0 12px 34px rgba(90,80,180,0.07);}
  .ex-head{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid var(--border);}
  .ex-head h2{font-size:17.5px;font-weight:800;margin:0;color:#191d33;}
  .type-pill{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--text-faint);background:var(--bg);border:1px solid var(--border);padding:4px 9px;border-radius:99px;white-space:nowrap;}
  .wordbank{font-size:12.5px;background:var(--accent-soft);border:1px solid #e2ddff;padding:10px 14px;border-radius:12px;margin-bottom:18px;color:#544a9e;line-height:1.5;}
  .item{padding:16px 0;border-bottom:1px solid var(--border);}
  .item:last-of-type{border-bottom:none;}
  .item-top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;}
  .prompt{font-size:14.5px;line-height:1.6;flex:1;}
  .num{color:var(--accent);font-weight:800;margin-right:6px;}
  .btn-row{display:flex;gap:6px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end;}
  .mini-btn{font-size:11.5px;font-weight:700;padding:6px 11px;border-radius:8px;cursor:pointer;border:1px solid transparent;white-space:nowrap;font-family:inherit;}
  .mini-btn.hint{color:var(--gold);background:var(--gold-soft);border-color:#f3dba3;}
  .mini-btn.check{color:#fff;background:var(--accent);}
  .mini-btn.check:disabled{opacity:.4;cursor:default;}
  .mini-btn.self{font-size:11px;padding:5px 9px;border:1px solid var(--border);background:var(--bg);color:var(--text-dim);}
  .hint-text{font-size:12.5px;color:#a3730e;margin-top:8px;background:var(--gold-soft);padding:8px 12px;border-radius:9px;line-height:1.5;}
  .blank-input{font-family:inherit;border:none;border-bottom:2px solid var(--border);background:transparent;font-size:14.5px;padding:2px 6px;min-width:130px;max-width:100%;color:var(--accent);font-weight:700;margin:0 2px;}
  .blank-input:focus{outline:none;border-bottom-color:var(--accent);}
  .blank-input.wide{width:100%;margin-top:8px;}
  .mc-options{display:flex;flex-direction:column;gap:6px;margin-top:10px;}
  .mc-option{font-size:13.5px;padding:9px 13px;border:1.5px solid var(--border);border-radius:10px;cursor:pointer;background:var(--bg);transition:all .12s ease;display:flex;align-items:center;gap:8px;}
  .mc-option:hover{border-color:var(--accent);}
  .mc-option.selected{border-color:var(--accent);background:var(--accent-soft);}
  .mc-option.dimmed{opacity:.35;pointer-events:none;text-decoration:line-through;}
  .mc-option.correct{background:var(--mint-soft);border-color:var(--mint);color:#0e7c58;font-weight:700;}
  .mc-option.incorrect{background:var(--coral-soft);border-color:var(--coral);color:#c23930;}
  .mc-icon{font-size:12px;width:16px;text-align:center;flex-shrink:0;}
  .feedback{font-size:12.5px;margin-top:8px;padding:8px 12px;border-radius:9px;line-height:1.5;}
  .feedback.correct{color:#0e7c58;background:var(--mint-soft);}
  .feedback.incorrect{color:#c23930;background:var(--coral-soft);}
  .feedback .ans{font-weight:800;}
  .reveal-answer{font-size:12.5px;color:var(--text-dim);margin-top:8px;padding:10px 13px;background:var(--bg);border-radius:10px;border:1px solid var(--border);line-height:1.5;}
  .reveal-answer b{color:var(--mint);}
  .self-grade-row{margin-top:8px;display:flex;gap:6px;align-items:center;}
  .self-grade-row span{font-size:11.5px;color:var(--text-faint);}
  .nav-row{display:flex;justify-content:space-between;margin-top:20px;}
  .nav-row button{font-family:inherit;font-size:13px;font-weight:700;background:var(--card);border:1px solid var(--border);color:var(--text-dim);padding:9px 16px;border-radius:10px;cursor:pointer;}
  .nav-row button:disabled{opacity:.25;cursor:default;}
  .summary-box{text-align:center;font-size:12.5px;color:var(--text-faint);margin-top:16px;}
  .prog-row{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid var(--border);}
  .prog-row:last-child{border-bottom:none;}
  .prog-word{font-size:13.5px;font-weight:700;width:160px;flex-shrink:0;color:#191d33;}
  .prog-bar-track{flex:1;height:8px;background:var(--bg);border-radius:99px;overflow:hidden;border:1px solid var(--border);}
  .prog-bar-fill{height:100%;border-radius:99px;}
  .prog-pct{font-size:12px;font-weight:700;width:42px;text-align:right;color:var(--text-dim);flex-shrink:0;}
  .prog-empty{font-size:13px;color:var(--text-faint);text-align:center;padding:30px 0;}
  .export-area{margin-top:18px;}
  .export-area textarea{width:100%;min-height:120px;font-family:ui-monospace,monospace;font-size:11.5px;border:1px solid var(--border);border-radius:10px;padding:10px;background:var(--bg);color:var(--text-dim);resize:vertical;}
  .export-label{font-size:12px;color:var(--text-faint);margin-bottom:6px;}
  @media (max-width:600px){.card{padding:18px 16px 16px;}.item-top{flex-direction:column;}.btn-row{justify-content:flex-start;}.prog-word{width:110px;}}
</style>
<div class="wrap">
  <div class="top">
    <div class="eyebrow">Murat's English Journey</div>
    <h1>__TITLE__</h1>
    <p>__SUBTITLE__</p>
  </div>
  <div class="mode-switch">
    <div class="mode-btn active" id="modePractice">Practice</div>
    <div class="mode-btn" id="modeProgress">Progress</div>
  </div>
  <div id="practiceView">
    <div class="progress-track"><div class="progress-fill" id="progressFill" style="width:0%"></div></div>
    <div class="tabs" id="tabs"></div>
    <div class="card">
      <div id="exerciseArea"></div>
      <div class="nav-row"><button id="prevBtn">← previous</button><button id="nextBtn">next →</button></div>
    </div>
    <div class="summary-box" id="overallSummary"></div>
  </div>
  <div id="progressView" style="display:none;">
    <div class="card">
      <div class="ex-head"><h2>Word mastery — this session</h2><span class="type-pill">not saved after reload</span></div>
      <div id="progressList"></div>
      <div class="export-area">
        <div class="export-label">Optional: copy this back to Claude if you want to talk about it.</div>
        <textarea id="exportText" readonly></textarea>
      </div>
    </div>
  </div>
</div>
<script>
function firstLetter(answer){ return answer.split(' ').map(w => w[0] + '_'.repeat(Math.max(w.length-1,0))).join(' '); }
const exercises = __EXERCISES__;
let current = 0, mode = 'practice', mastery = {};
const state = exercises.map(ex => ({
  itemChecked:new Array(ex.items.length).fill(false), itemCorrect:new Array(ex.items.length).fill(null),
  answers:new Array(ex.items.length).fill(null), hints:new Array(ex.items.length).fill(false),
  dimmedOption:new Array(ex.items.length).fill(null)}));
function norm(s){ return (s||'').trim().toLowerCase().replace(/[’']/g,"'").replace(/\s+/g,' ').replace(/[.!?]+$/,''); }
function recordResult(target, correct){
  if(!mastery[target]) mastery[target] = {label:target, correct:0, attempts:0};
  mastery[target].attempts += 1; if(correct) mastery[target].correct += 1;
}
function renderTabs(){
  const tabs = document.getElementById('tabs'); tabs.innerHTML = '';
  exercises.forEach((ex,i)=>{
    const allDone = state[i].itemChecked.every(c=>c);
    const t = document.createElement('div');
    t.className = 'tab' + (i===current?' active':'') + (allDone?' done':'');
    t.textContent = ex.id; t.title = ex.title; t.onclick = ()=>{ current = i; render(); };
    tabs.appendChild(t);
  });
  const totalItems = exercises.reduce((a,ex)=>a+ex.items.length,0);
  const doneItems = state.reduce((a,s)=>a+s.itemChecked.filter(c=>c).length,0);
  document.getElementById('progressFill').style.width = (doneItems/totalItems*100) + '%';
}
function render(){
  if(mode!=='practice') return;
  renderTabs();
  const ex = exercises[current], st = state[current], area = document.getElementById('exerciseArea');
  area.innerHTML = '';
  const head = document.createElement('div'); head.className = 'ex-head';
  const typeLabel = ex.type==='mc' ? 'multiple choice' : ex.type==='reveal' ? 'correct the mistake' : 'fill the blank';
  const h2 = document.createElement('h2'); h2.textContent = ex.title;
  const pill = document.createElement('span'); pill.className = 'type-pill'; pill.textContent = typeLabel;
  head.appendChild(h2); head.appendChild(pill); area.appendChild(head);
  if(ex.note){ const wb = document.createElement('div'); wb.className = 'wordbank'; wb.textContent = ex.note; area.appendChild(wb); }
  ex.items.forEach((it,i)=>{
    const div = document.createElement('div'); div.className = 'item';
    const top = document.createElement('div'); top.className = 'item-top';
    const checked = st.itemChecked[i];
    const num = ()=>{ const s=document.createElement('span'); s.className='num'; s.textContent=(i+1)+'.'; return s; };
    if(ex.type === 'fill'){
      const parts = it.prompt.split('___');
      const p = document.createElement('div'); p.className = 'prompt';
      p.appendChild(num()); p.appendChild(document.createTextNode(parts[0]));
      const input = document.createElement('input'); input.className = 'blank-input'; input.placeholder = '...';
      input.value = st.answers[i] || ''; input.disabled = checked;
      input.oninput = ()=>{ st.answers[i] = input.value; };
      input.onkeydown = (e)=>{ if(e.key==='Enter' && !checked) checkFillItem(i); };
      p.appendChild(input); p.appendChild(document.createTextNode(parts.slice(1).join('___')));
      top.appendChild(p);
      const btnRow = document.createElement('div'); btnRow.className = 'btn-row';
      const hb = document.createElement('button'); hb.className = 'mini-btn hint'; hb.textContent = 'Hint';
      hb.onclick = ()=>{ st.hints[i] = !st.hints[i]; render(); }; btnRow.appendChild(hb);
      if(!checked){ const cb = document.createElement('button'); cb.className = 'mini-btn check'; cb.textContent = 'Check'; cb.onclick = ()=> checkFillItem(i); btnRow.appendChild(cb); }
      top.appendChild(btnRow); div.appendChild(top);
      if(st.hints[i]){ const ht = document.createElement('div'); ht.className = 'hint-text';
        ht.textContent = `${it.meaning ? it.meaning + ' — ' : ''}starts like "${firstLetter(it.answers[0])}"`; div.appendChild(ht); }
      if(checked){ const ok = st.itemCorrect[i]; const fb = document.createElement('div'); fb.className = 'feedback ' + (ok?'correct':'incorrect');
        if(ok) fb.textContent = '✓ correct';
        else { fb.appendChild(document.createTextNode(`✗ your answer: "${st.answers[i] || '(blank)'}" — correct: `));
          const a=document.createElement('span'); a.className='ans'; a.textContent=it.answers[0]; fb.appendChild(a); }
        div.appendChild(fb); }
    }
    if(ex.type === 'mc'){
      const p = document.createElement('div'); p.className = 'prompt'; p.appendChild(num()); p.appendChild(document.createTextNode(it.prompt));
      top.appendChild(p);
      const btnRow = document.createElement('div'); btnRow.className = 'btn-row';
      const hb = document.createElement('button'); hb.className = 'mini-btn hint'; hb.textContent = 'Hint';
      hb.onclick = ()=>{ if(checked) return;
        const wrongIdx = it.options.map((_,oi)=>oi).filter(oi=>oi!==it.correct);
        st.dimmedOption[i] = wrongIdx[Math.floor(Math.random()*wrongIdx.length)]; st.hints[i] = true; render(); };
      btnRow.appendChild(hb); top.appendChild(btnRow); div.appendChild(top);
      if(st.hints[i] && it.meaning){ const ht = document.createElement('div'); ht.className = 'hint-text'; ht.textContent = it.meaning; div.appendChild(ht); }
      const opts = document.createElement('div'); opts.className = 'mc-options';
      it.options.forEach((optText,oi)=>{
        const o = document.createElement('div'); o.className = 'mc-option';
        if(!checked && st.answers[i] === oi) o.classList.add('selected');
        if(!checked && st.dimmedOption[i] === oi) o.classList.add('dimmed');
        let icon = String.fromCharCode(97+oi)+')';
        if(checked){ if(oi === it.correct){ o.classList.add('correct'); icon = '✓'; } else if(oi === st.answers[i]){ o.classList.add('incorrect'); icon = '✗'; } }
        const ic=document.createElement('span'); ic.className='mc-icon'; ic.textContent=icon;
        const tx=document.createElement('span'); tx.textContent=optText; o.appendChild(ic); o.appendChild(tx);
        o.onclick = ()=>{ if(checked) return; st.answers[i] = oi; render(); };
        opts.appendChild(o);
      });
      div.appendChild(opts);
      if(!checked){ const cb = document.createElement('button'); cb.className = 'mini-btn check'; cb.style.marginTop = '10px'; cb.textContent = 'Check';
        cb.disabled = st.answers[i]===null || st.answers[i]===undefined; cb.onclick = ()=> checkMcItem(i); div.appendChild(cb); }
    }
    if(ex.type === 'reveal'){
      const p = document.createElement('div'); p.className = 'prompt'; p.appendChild(num()); p.appendChild(document.createTextNode(it.prompt));
      top.appendChild(p);
      const btnRow = document.createElement('div'); btnRow.className = 'btn-row';
      const hb = document.createElement('button'); hb.className = 'mini-btn hint'; hb.textContent = 'Hint';
      hb.onclick = ()=>{ st.hints[i] = !st.hints[i]; render(); }; btnRow.appendChild(hb);
      top.appendChild(btnRow); div.appendChild(top);
      if(st.hints[i]){ const ht = document.createElement('div'); ht.className = 'hint-text'; ht.textContent = it.hint; div.appendChild(ht); }
      const input = document.createElement('input'); input.className = 'blank-input wide'; input.placeholder = 'write the corrected sentence...';
      input.value = st.answers[i] || ''; input.disabled = checked; input.oninput = ()=>{ st.answers[i] = input.value; };
      div.appendChild(input);
      if(!checked){ const cb = document.createElement('button'); cb.className = 'mini-btn check'; cb.style.marginTop = '10px'; cb.textContent = 'Reveal answer'; cb.onclick = ()=> revealItem(i); div.appendChild(cb); }
      if(checked){
        const ra = document.createElement('div'); ra.className = 'reveal-answer';
        const b=document.createElement('b'); b.textContent='Model answer: '; ra.appendChild(b); ra.appendChild(document.createTextNode(it.answer)); div.appendChild(ra);
        if(st.itemCorrect[i] === null){
          const sg = document.createElement('div'); sg.className = 'self-grade-row';
          const lab=document.createElement('span'); lab.textContent='Did you get it right?'; sg.appendChild(lab);
          const rightBtn = document.createElement('button'); rightBtn.className = 'mini-btn self right'; rightBtn.textContent = '✓ Yes';
          const wrongBtn = document.createElement('button'); wrongBtn.className = 'mini-btn self wrong'; wrongBtn.textContent = '✗ No';
          rightBtn.onclick = ()=>{ st.itemCorrect[i]=true; recordResult(it.target, true); render(); };
          wrongBtn.onclick = ()=>{ st.itemCorrect[i]=false; recordResult(it.target, false); render(); };
          sg.appendChild(rightBtn); sg.appendChild(wrongBtn); div.appendChild(sg);
        } else {
          const fb=document.createElement('div'); fb.className='feedback '+(st.itemCorrect[i]?'correct':'incorrect');
          fb.textContent = st.itemCorrect[i] ? '✓ you marked this right' : '✗ you marked this wrong'; div.appendChild(fb);
        }
      }
    }
    area.appendChild(div);
  });
  document.getElementById('prevBtn').disabled = current===0;
  document.getElementById('nextBtn').disabled = current===exercises.length-1;
  renderSummary();
}
function checkFillItem(i){ const it = exercises[current].items[i], st = state[current];
  const val = norm(st.answers[i] || ''); const ok = it.answers.some(a=>norm(a)===val);
  st.itemChecked[i] = true; st.itemCorrect[i] = ok; recordResult(it.target, ok); render(); }
function checkMcItem(i){ const it = exercises[current].items[i], st = state[current];
  const ok = st.answers[i] === it.correct; st.itemChecked[i] = true; st.itemCorrect[i] = ok; recordResult(it.target, ok); render(); }
function revealItem(i){ state[current].itemChecked[i] = true; render(); }
function renderSummary(){
  const totalItems = exercises.reduce((a,ex)=>a+ex.items.length,0);
  const doneItems = state.reduce((a,s)=>a+s.itemChecked.filter(c=>c).length,0);
  let correctCount = 0, gradedTotal = 0;
  state.forEach((s,ei)=>{ if(exercises[ei].type==='reveal') return;
    s.itemChecked.forEach((c,i)=>{ if(c){ gradedTotal++; if(s.itemCorrect[i]) correctCount++; } }); });
  document.getElementById('overallSummary').textContent = `${doneItems} / ${totalItems} items checked` + (gradedTotal>0 ? ` · ${correctCount}/${gradedTotal} correct` : '');
}
function renderProgress(){
  const list = document.getElementById('progressList'); const keys = Object.keys(mastery);
  if(keys.length===0){ list.innerHTML = '<div class="prog-empty">No words checked yet. Results for this session appear here.</div>'; document.getElementById('exportText').value = ''; return; }
  const rows = keys.map(k=>{ const m = mastery[k]; return {label:m.label, pct:Math.round((m.correct/m.attempts)*100), attempts:m.attempts}; }).sort((a,b)=>a.pct-b.pct);
  list.innerHTML = '';
  rows.forEach(r=>{ const row = document.createElement('div'); row.className = 'prog-row';
    const color = r.pct>=80 ? 'var(--mint)' : r.pct>=50 ? 'var(--gold)' : 'var(--coral)';
    const w=document.createElement('div'); w.className='prog-word'; w.textContent=r.label;
    const tr=document.createElement('div'); tr.className='prog-bar-track'; const f=document.createElement('div'); f.className='prog-bar-fill'; f.style.width=r.pct+'%'; f.style.background=color; tr.appendChild(f);
    const pc=document.createElement('div'); pc.className='prog-pct'; pc.textContent=r.pct+'%';
    row.appendChild(w); row.appendChild(tr); row.appendChild(pc); list.appendChild(row); });
  document.getElementById('exportText').value = `Vocabulary practice — session results (${new Date().toISOString().slice(0,10)})\n${rows.length} words practised\n\n` +
    rows.map(r=>`${r.label} — ${r.pct}% (${r.attempts} attempt${r.attempts>1?'s':''})`).join('\n');
}
document.getElementById('modePractice').onclick = ()=>{ mode='practice'; document.getElementById('modePractice').classList.add('active'); document.getElementById('modeProgress').classList.remove('active');
  document.getElementById('practiceView').style.display='block'; document.getElementById('progressView').style.display='none'; render(); };
document.getElementById('modeProgress').onclick = ()=>{ mode='progress'; document.getElementById('modeProgress').classList.add('active'); document.getElementById('modePractice').classList.remove('active');
  document.getElementById('practiceView').style.display='none'; document.getElementById('progressView').style.display='block'; renderProgress(); };
document.getElementById('prevBtn').onclick = ()=>{ if(current>0){current--; render(); window.scrollTo(0,0);} };
document.getElementById('nextBtn').onclick = ()=>{ if(current<exercises.length-1){current++; render(); window.scrollTo(0,0);} };
render();
</script>
"""

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
```

<!-- file: record.py -->
```python
"""Record one review for each word practised in a vocab session, on Murat's ledger lists.

Usage: python3 record.py vocab_tracker.json pv_tracker.json practised.txt DD.MM.YYYY
practised.txt: one expression per line, spelled exactly as on the list (vocab `expr`,
or the phrasal verb's `word`). Writes vocab_rows.json and pv_rows.json ({"rows": [...]})
ready for `ledger.py stage` with `:merge`, and prints what changed.

Same rule as the naturalness check's vt_apply.py: +1 practice.count and practice.last =
the date, at most once per day. So if the naturalness check later records the same words
for the same day, nothing is counted twice. Practice never touches `dates` (unprompted uses)
or `mastered`. Words from a fresh source (not on either list) are reported and skipped:
only Murat adds items to the lists.
"""
import json, sys

def main(vpath, ppath, words_path, date):
    v = json.load(open(vpath)); p = json.load(open(ppath))
    by_v = {r["expr"].strip().lower(): r for r in v["rows"]}
    by_p = {r["word"].strip().lower(): r for r in p["rows"]}
    done, same_day, missing, vc, pc = [], [], [], 0, 0
    for w in (l.strip() for l in open(words_path, encoding="utf-8")):
        if not w: continue
        r, where = by_v.get(w.lower()), "vocab"
        if r is None: r, where = by_p.get(w.lower()), "pv"
        if r is None: missing.append(w); continue
        pr = r.setdefault("practice", {"count": 0, "last": None})
        if pr.get("last") == date: same_day.append(w); continue
        pr["count"] = (pr.get("count") or 0) + 1; pr["last"] = date
        done.append(f'{w} ({where}, now {pr["count"]}x)')
        if where == "vocab": vc += 1
        else: pc += 1
    json.dump({"rows": v["rows"]}, open("vocab_rows.json", "w"), ensure_ascii=False)
    json.dump({"rows": p["rows"]}, open("pv_rows.json", "w"), ensure_ascii=False)
    print(f"{len(done)} reviews recorded ({vc} on the vocab list, {pc} on the phrasal verb list)")
    for d in done: print("  +", d)
    if same_day: print("ALREADY RECORDED TODAY:", "; ".join(same_day))
    if missing: print("NOT ON EITHER LIST (skipped):", "; ".join(missing))
    print("WRITE:", "vocab" if vc else "", "pv" if pc else "")

if __name__ == "__main__":
    main(*sys.argv[1:5])
```

<!-- file: pagetest.py -->
```python
"""Open the built quiz in Chromium and click through it before delivery.

Usage: python3 pagetest.py quiz.html
Checks: no page errors, 11 exercise tabs, every item renders, a right answer is marked
correct, a wrong one is marked wrong with the answer shown, hints appear, the Progress view
fills in, and the page fits a 390 px phone screen without sideways scrolling.
"""
import sys, json, pathlib
from playwright.sync_api import sync_playwright

def main(path):
    # The platform wraps the published file in a doctype/head/body skeleton; do the same here.
    wrapped = pathlib.Path(path + ".preview.html")
    wrapped.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>'
        + pathlib.Path(path).read_text() + '</body></html>')
    url = wrapped.resolve().as_uri()
    data = json.load(open(path + ".data.json"))
    fails, errs = [], []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page(viewport={"width": 1200, "height": 900})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url)
        if pg.locator(".tab").count() != 11: fails.append("expected 11 tabs")
        for e, ex in enumerate(data):
            pg.locator(".tab").nth(e).click()
            if pg.locator(".item").count() != len(ex["items"]): fails.append(f"exercise {e+1}: item count")
        # first fill exercise: right then wrong
        f = next(i for i, x in enumerate(data) if x["type"] == "fill")
        pg.locator(".tab").nth(f).click()
        it = pg.locator(".item")
        it.nth(0).locator(".blank-input").fill(data[f]["items"][0]["answers"][0])
        it.nth(0).locator(".mini-btn.check").click()
        if "correct" not in (it.nth(0).locator(".feedback").get_attribute("class") or ""): fails.append("right answer not accepted")
        it.nth(1).locator(".mini-btn.hint").click()
        if it.nth(1).locator(".hint-text").count() != 1: fails.append("fill hint missing")
        it.nth(1).locator(".blank-input").fill("zzz")
        it.nth(1).locator(".mini-btn.check").click()
        if "incorrect" not in (it.nth(1).locator(".feedback").get_attribute("class") or ""): fails.append("wrong answer not marked")
        # first MC exercise: pick the right option
        m = next(i for i, x in enumerate(data) if x["type"] == "mc")
        pg.locator(".tab").nth(m).click()
        it = pg.locator(".item")
        it.nth(0).locator(".mc-option").nth(data[m]["items"][0]["correct"]).click()
        it.nth(0).locator(".mini-btn.check").click()
        if it.nth(0).locator(".mc-option.correct").count() != 1: fails.append("MC check failed")
        pg.locator("#modeProgress").click()
        if pg.locator(".prog-row").count() < 1: fails.append("progress view empty")
        pg.set_viewport_size({"width": 390, "height": 844})
        pg.locator("#modePractice").click()
        sw = pg.evaluate("document.documentElement.scrollWidth")
        if sw > 390: fails.append(f"too wide on a phone ({sw}px)")
        b.close()
    if errs: fails.append("page errors: " + "; ".join(errs))
    print("PAGE TEST PASSED" if not fails else "PAGE TEST FAILED:\n  " + "\n  ".join(fails))
    if fails: raise SystemExit(1)

if __name__ == "__main__":
    main(sys.argv[1])
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
