---
name: "chunk-update"
description: "Update Murat's chunk list (the small precision targets tracked in his speech): show each chunk's status and evidence from the Fluency Ledger, open, settle or add chunks and grammar slices on his say-so, and copy the open/settled list into the Prepositions & Collocations quiz. Trigger on \"let's update the chunks\", \"update the chunks\", \"open chunk N\", \"settle chunk N\", \"add a new chunk\" or \"chunk status\" in My English Journey."
---

# Update the chunks

Murat tracks a few small precision targets at a time: **chunks** (prepositions and other
Turkish-shaped patterns) and **grammar slices** (one narrow tense point). The list lives in the
Fluency Ledger as `meta/chunks`; the naturalness check counts correct and wrong uses of every
**open** item in his speech; the Ledger's Chunks tab pools them. This skill is the only place the
list changes, and it changes only on Murat's word.

**Tracked vs focus (Murat's decisions, 12.10.26).** Every item is tracked (`status: "open"`) from day
one, because he may get one right before its date. `focus: true` marks what the dated plan says to
work on now: the quiz gives focus items about 70% of a chunk session (the other open ones about
20%, settled ones about 10%), and the Mini Prompt lists focus items first. Any item settles under
the same rule (last 12 voice uses at 80%+, over at least 4 sessions), focus or not, whatever its
dates. The dates change only when he changes them.

- Ledger: https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK (`meta/chunks`, the `sessions` collection)
- Quiz: https://claude.ai/artifact/TZebyGZWe6Mu6Xtmq4UpLy (its own db; this skill writes `chunks/state`)
- Plan and definitions: https://claude.ai/artifact/Kmeozvrx9sSpppVH9cE7Gf

**Murat decides.** Never open, settle or drop an item on your own, even when the numbers say it is
ready. Suggest; he confirms. Ask one question at a time.

## Step 1: Read the current state (no writes)

1. `ArtifactData` `get` on the Ledger: collection `meta`, doc `chunks`, with `out_dir: /tmp/cu`.
   Note its `version`.
2. `ArtifactData` `list` on the Ledger: collection `sessions`, `out_dir: /tmp/cu`.
3. `ArtifactData` `get` on the **quiz**: collection `chunks`, doc `state`. Note its `version`, or that
   it doesn't exist yet (the first run creates it).
4. Copy this skill's `scripts/status.py` to `/tmp/cu` and run:
   `python3 /tmp/cu/status.py /tmp/cu/meta/chunks.json /tmp/cu/sessions`

## Step 2: Show Murat where things stand

Short, from the script output only (never estimate):
- each **focus** item: last-12 accuracy, how many uses and sessions so far, ahead / on track /
  behind its draft dates, and "ready to settle" if the script says so;
- the other tracked items in one line each, and any of them that is "ready to settle" early;
- **settled** items that have slipped below the target since (still tracked);
- what is next in the draft plan.
Then ask what he wants to change. Typical answers: settle one, open the next one, change a date,
add or edit a definition, add a new chunk.

## Step 3: Make the change in a copy of `meta/chunks`

Edit `/tmp/cu/meta/chunks.json` (the data only, not the wrapper), then:
- **settle**: `status: "settled"`, add `settled_on: "YYYY-MM-DD"` (today), `focus: false`;
- **focus** on an item: `focus: true` (and `focus: false` on the one it replaces, if he says so);
- **reopen** a settled item: `status: "open"`, keep `settled_on` history in `note`;
- **new item**: id `c6`, `c7`... or `s5`, `s6`...; every field the others have: `layer`, `n`, `title`,
  `status` (`open`), `focus`, `planned`, `difficulty`, `counts`, `correct`, `wrong`, `left_out`, `examples` (at least
  one, marked `yours: true` when it is his own sentence), and `words` when the chunk is a closed list.
  Draft the definition with him, item by item, before writing. A definition must say exactly what
  counts and what is left out; vague items can't be counted.
- bump `version` by 1 and set `as_of` to today.
Never change `rule` unless he asks for it explicitly.

**Two limits to tell him when they apply:**
- **Counting.** The naturalness check can count only items it has a finder for (all nine of c1–c5 and
  s1–s4 since 12.10.26; `status.py` marks any other "can't count this one yet"). A new item is fine
  to add: the check counts the ones it can and says which it can't. A finder for a new item is code in
  `naturalness-check/scripts/chunks.py`, built and tested in a Claude Code session (repo
  `kmuratcigir/claude-phrasal-verbs`, folder `ledger/skill`), then uploaded with the skill.
- **Quiz items.** Chunks c1–c5 and slices s1–s4 have quiz items. A new item has none until they are
  written and approved (also a Claude Code job, `prep-quiz/src/bank_chunks.js`); until then the quiz
  ignores it.

## Step 4: Save, two approvals

The Ledger and the quiz are separate pages with separate databases, so this takes two writes:
1. Ledger: `ArtifactData` `set` collection `meta`, doc `chunks`, `file_path: /tmp/cu/meta/chunks.json`,
   `if_version` from Step 1.
2. Quiz: `ArtifactData` `set` collection `chunks`, doc `state`, data
   `{"open": [ids with status open], "focus": [ids with focus true], "settled": [ids with status settled], "as_of": "<today YYYY-MM-DD>", "source": "ledger"}`,
   with `if_version` from Step 1 if the doc existed. Ids the quiz doesn't know are ignored there.
If a write fails because the doc changed meanwhile, read it again, redo the edit, and write again.
Never write `sessions`, `meta/overview` or any other Ledger doc from here.

## Step 5: Confirm

One short message: what changed, what is open now, that the Ledger's Chunks tab and the quiz's
Chunks tab both show it, and any limit from Step 3 that applies (an item the check can't count yet,
or one with no quiz items). If he opened something new, add one line on what counts for it, in
his words where possible, so he can start using it in speech.
