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

- Ledger: https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK (files `data/meta/chunks.json` and `data/sessions/`)
- Quiz: https://claude.ai/artifact/TZebyGZWe6Mu6Xtmq4UpLy (its own db; this skill writes `chunks/state`)
- Plan and definitions: https://claude.ai/artifact/Kmeozvrx9sSpppVH9cE7Gf

**Murat decides.** Never open, settle or drop an item on your own, even when the numbers say it is
ready. Suggest; he confirms. Ask one question at a time.

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
2. Check the ledger's current version id (chat: `get_artifact` or `list_files`; Claude Code:
   `Artifact` `list` with scope `files`). If it differs from the one you noted, something was saved
   in between: read the files you change again, rerun the scripts that build them, stage again.
3. Publish exactly the files the `PUBLISH:` line lists, from `<work>/publish`, each at its `data/…`
   path, as a new version of the ledger: in a chat, `publish_files`; in Claude Code, `Artifact`
   publish with `url` = the ledger, `file_path` = the ledger page saved by an `Artifact` `read` of
   the url (no `path`), `root` = `<work>/publish` and `files` = those paths. In a chat never send
   `index.html`. Files left out stay as they are.
4. Confirm with a file listing that the new version holds each published file at its staged size
   (`wc -c <work>/publish/data/...`). If the publish failed, nothing changed: say so plainly.

## Step 1: Read the current state (no writes)

1. Copy this skill's `scripts/status.py` and `scripts/ledger.py` to `/tmp/cu`.
2. Read the Ledger's files into `/tmp/cu` (see "The ledger's files"): `data/index.json`, then
   `data/meta/chunks.json` and every session the index lists (into `/tmp/cu/sessions/`). Then
   `python3 /tmp/cu/ledger.py snapshot /tmp/cu`.
3. Read the **quiz**'s own database doc: collection `chunks`, doc `state` (a small doc, so the
   database tools are fine here: `db_get` in a chat, `ArtifactData` `get` in Claude Code). Note its
   `version`, or that it doesn't exist yet (the first run creates it).
4. Run: `python3 /tmp/cu/status.py /tmp/cu/meta/chunks.json /tmp/cu/sessions`

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
- **Counting.** The naturalness check can count only items it has a finder for (c1–c5 and s1–s4 since
  12.10.26, s5–s7 since 29.10.26; `status.py` marks any other "can't count this one yet"). A new item is fine
  to add: the check counts the ones it can and says which it can't. A finder for a new item is code in
  `naturalness-check/scripts/chunks.py`, built and tested in a Claude Code session (repo
  `kmuratcigir/claude-phrasal-verbs`, folder `ledger/skill`), then uploaded with the skill.
- **Quiz items.** Chunks c1–c5 and slices s1–s4 have quiz items (s5–s7 have none yet). A new item has none until they are
  written and approved (also a Claude Code job, `prep-quiz/src/bank_chunks.js`); until then the quiz
  ignores it.

## Step 4: Save, two approvals

The Ledger and the quiz are separate pages, so this takes two saves:
1. Ledger: `python3 /tmp/cu/ledger.py stage /tmp/cu meta/chunks=meta/chunks.json`, then publish as
   "Saving" in "The ledger's files" says. On `REFUSED` (an item would be lost), stop and tell Murat.
2. Quiz: set its database doc, collection `chunks`, doc `state` (`db_write` op `set` in a chat,
   `ArtifactData` `set` in Claude Code), data
   `{"open": [ids with status open], "focus": [ids with focus true], "settled": [ids with status settled], "as_of": "<today YYYY-MM-DD>", "source": "ledger"}`,
   with `if_version` from Step 1 if the doc existed. Ids the quiz doesn't know are ignored there.
If a save fails because the file or doc changed meanwhile, read it again, redo the edit, and save again.
Never save `sessions`, `meta/overview` or any other Ledger file from here.

## Step 5: Confirm

One short message: what changed, what is open now, that the Ledger's Chunks tab and the quiz's
Chunks tab both show it, and any limit from Step 3 that applies (an item the check can't count yet,
or one with no quiz items). If he opened something new, add one line on what counts for it, in
his words where possible, so he can start using it in speech.
