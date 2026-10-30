---
name: "naturalness-check"
description: "Analyze Murat's English in the current practice chat (grammar, vocabulary, phrasal verbs and Turkish interference) with spaCy detectors and two blind reading passes, verify every flag, log the session and update the phrasal verb and vocabulary trackers on the Fluency Ledger dashboard, and report. Trigger only on \"naturalness check\" requests in My English Journey."
---

# Naturalness Check

Runs only when Murat triggers it ("naturalness check", "do a naturalness check", "let's do a
naturalness check"). Never run it automatically at the end of a session. It analyzes
everything Murat has said or written in the current chat (grammar, vocabulary and phrasal
verbs), checks it for Turkish interference (added 27.09.26), logs the result as one session on
the Fluency Ledger dashboard, updates the phrasal verb and vocabulary trackers stored there,
and reports back.

Since 26.09.26 this check also does the phrasal verb tracker's job (density against the
native benchmark, tracker come-ups, new words). The tracker lives in the ledger
(`meta/pv_tracker`), not in the .docx; the .docx is only an export, made on request with the
`phrasal-verb-tracker` skill. Never edit the .docx separately.

Since 27.09.26 Murat's vocabulary list lives in the ledger too (`meta/vocab_tracker`), and
this check keeps it up to date the same way: a verified, unprompted use of a list word adds
the day to that word; words drilled in this chat's vocab session count as a review, never as
a use. Stages follow the phrasal verb tracker's rules. Only Murat adds words to the list,
and `mastered` is his own label: this check never adds rows and never changes `mastered`.
Examples and stories are no longer recorded. The old "English Vocabulary Practice" .docx is
retired (an export can be made on request); never read the list from it.

Since 27.09.26 (later that day) the study list is split in two: `meta/vocab_tracker` holds
words, idioms and expressions only, and the phrasal verbs from Murat's list live in
`meta/pv_tracker` as rows with a `list` block (`{ids, exprs, added, importance, mastered}`,
shown as "list" on the dashboard). Their vocab-session reviews sit on the row as `practice:
{count, last}`. Phrasal verbs are stored in their base form ("snap out of", "catch up with").
Prepositional verbs ("dwell on", "cope with", "appeal to") count as phrasal verbs too (Murat's
call). When Murat adds a phrasal verb to his list, it goes into `meta/pv_tracker` (add a `list`
block to the existing row, or a new row); any other item goes into `meta/vocab_tracker` with a
`type`: `word`, `collocation`, `expression` or `idiom` (the dashboard filters by it).

Since 30.09.26 the check also keeps the ledger's **Overview** tab current (the first tab: a
CEO-style brief on the whole journey). Every mistake gets an **impact** label (changes the
meaning / sounds foreign / slip), the day's text report is saved with the session, and Claude
rewrites the brief (`meta/overview`) from all session docs. All of it goes into the same single
save, so it is still one approval. Murat's words for the brief: "put a story behind the
numbers", frank both ways, like an executive report.

Since 12.10.26 the check also tracks Murat's **chunks**: a few small targets at a time
(prepositions, Turkish-shaped patterns, grammar slices), listed in `meta/chunks` with exact
"what counts" definitions. Since 12.10.26 (later that day) **every** chunk and slice is tracked
(status `open`) from day one, not only the current one: Murat may get one right before its date.
`focus: true` marks what the dated plan says to work on now; it doesn't change what is counted.
For every open item the check counts correct *and* wrong uses in his speech (a script finds
candidates, Claude checks each one) and stores them in the session doc as a `chunks` block. The
Ledger's Chunks tab pools them across sessions: any item is "settled" when its last 12 voice uses
are at 80% or better, spread over at least 4 sessions, whatever its dates. The check
**never changes `meta/chunks`**: only Murat opens, settles or adds chunks. Plan:
https://claude.ai/artifact/Kmeozvrx9sSpppVH9cE7Gf

Since 16.10.26 the check also counts **preposition accuracy** for the Ledger's Prepositions tab.
`preps.py` lists every word + preposition pair Murat said or wrote (voice and typed both count);
a use is wrong when this check flagged it as a preposition slip (`preposition_case` or
`err_preposition`) and right otherwise. It stores the counts in the session doc as a `preps`
block and updates the watch list `meta/prep_watch` (one row per word Murat said; a word joins
the list on its second slip, after one slip it waits). It is one command in Step 5 and goes into
the same single save. It fails softly: if it can't run, the check carries on without it.

Since 28.10.26 the report also gives **sentences with a slip**: the share of voice sentences
holding at least one counted error (Step 6, part 0). Report only, no dashboard chart (Murat's
choice, 28.10.26).

Why it is built this way (rebuilt 25.09.26): the earlier version asked Claude to read the
transcript and "notice" patterns. On a real 100+ minute thread that found 5 items. The same
thread through this pipeline gave 186 verified observations and 24 real errors. The difference:
scripts parse every sentence and flag every match mechanically, and Claude's job is to
check each flag, not to find them. Do not replace any step below with "just read it and
judge". That is the approach that failed.

Dashboard: https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK ("Fluency Ledger").
Its data files (see "The ledger's files" below) hold `meta/registry` (grammar concept ids → [label, CEFR level]),
`meta/vocab_tracker` (Murat's vocabulary list: `{as_of, max_id, rows: [{id, expr, added,
importance, mastered, practice: {count, last}, dates[], notes}]}`; `dates` = days used unprompted),
`meta/pv_tracker` (the phrasal verb tracker: `{as_of, rows: [{word, dates[], notes, list?, practice?}]}`;
`list` marks a phrasal verb on Murat's study list),
`meta/interference` (the Turkish-interference pattern list: `{types, patterns: [{key, label, turkish,
type, fix}]}`), `meta/overview` (the Overview tab's written brief, since 30.09.26) and one document
per checked chat in `sessions`.

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

## Step 1: Set up the tools

The thirteen scripts (`chunks.py` added 12.10.26, `preps.py` 16.10.26, `ledger.py` 30.10.26) and the interference pass instructions are separate files in this skill's `scripts/`
folder (since 06.10.26; until v23 they were embedded at the bottom of this file, which loaded about
100,000 characters of code into every check without need). Copy them into a work folder, using the
skill's base directory (shown when the skill loads), and fetch the CEFR wordlists. **Run them, don't
read them**: their output is all you need. Open a script only if it fails and you must see why.

**Start clean (added 30.09.26).** Files left in `/tmp/nc` by an earlier or failed attempt in this
chat (a half-written `murat_turns.txt`, old pass files, old outputs) must never mix into this
check: the turns file is appended to, so an old one would double or corrupt it (on 29.09.26 a
partial 89-turn file from a failed attempt was still there). The first command below empties the
folder, keeping only the wordlist clone.

```bash
mkdir -p /tmp/nc && find /tmp/nc -mindepth 1 -maxdepth 1 ! -name olp -exec rm -rf {} + && cd /tmp/nc
cp "<SKILL_BASE_DIR>"/scripts/* /tmp/nc/ && ls /tmp/nc/*.py /tmp/nc/*.md
python3 -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null || \
  { pip install --break-system-packages -q spacy && python3 -m spacy download en_core_web_sm; }
[ -d /tmp/nc/olp ] || git clone -q --depth 1 https://github.com/openlanguageprofiles/olp-en-cefrj /tmp/nc/olp
python3 -c "import wordfreq" 2>/dev/null || pip install --break-system-packages -q wordfreq
```

`wordfreq` only supplies a starting guess for the level of off-list words (Step 4). If it
won't install, vocab.py still runs; the suggestions are just blank and you assign every
off-list level yourself.

Then read the ledger's files into `/tmp/nc` (see "The ledger's files" above): `data/index.json`
first, then the `meta` files `vocab_tracker`, `pv_tracker`, `interference`, `phave`, `registry`,
`lexicon`, `overview`, `chunks` and `prep_watch` (they land in `/tmp/nc/meta/`), then every session
the index lists (into `/tmp/nc/sessions/`). `meta/chunks` is read-only for this check: never save it.
(`meta/vocab_items` is the old copy of the list from before 27.09.26; don't read it.) Step 6 builds
the brief from all the sessions, Step 8 compares with the previous one, and the index tells you
whether this chat's doc already exists (a second check in the same chat). Then take the baseline
the save is checked against:

```bash
cd /tmp/nc && python3 ledger.py snapshot /tmp/nc
```

It prints the row counts of every list. If it prints `REFUSED`, `index.json` is missing: read it.

**One save, one approval (28.09.26).** The app asks Murat to approve every save to the ledger,
and it offers him no "always allow". So this check reads whatever it needs up front and saves
**everything in a single publish in Step 7**: never an earlier save, never a follow-up save
afterwards. Reads don't change anything; keep all saving for Step 7.

If the skill's `scripts/` folder isn't readable from the sandbox (the `cp` fails, or fewer than the
thirteen scripts plus `intf_instructions.md` arrive), stop and tell Murat plainly: the check can't run
until the skill files are reachable. Never rewrite a script from memory. If spaCy can't be installed (no network to PyPI/GitHub), stop and tell
Murat plainly that the check can't run in this environment. Don't fall back to reading and
judging by eye. If only the wordlist clone fails, run the grammar part, skip vocabulary, and
say so in the report.

## Step 2: Recover the whole chat and save Murat's words

Long practice chats get compacted, so what's in context is not the full chat. Call
`mcp__claude_ai__read_conversation` with `conversation_id: "current"`, `max_turns: 50`, and
follow `next_page_token` until there is none. Note the chat id from the returned URL.

**Long chats: hand the reading to a helper (added 27.09.26).** A practice chat of an hour or
more gives very large pages (some come back saved to a file because they pass the tool's size
limit), and paging through them yourself fills your working context before the checking in
Step 4, which is the step that needs your full attention. So when the chat is long, or the
first page already shows big turns, give this step to a general-purpose subagent:
- tell it to page `read_conversation` (`conversation_id: "current"`, `max_turns: 50`) from the
  start, following `next_page_token` to the end, and give it the chat URL from the first page
  you read, which it must confirm before writing anything;
- tell it to append Murat's turns to `/tmp/nc/murat_turns.txt` in the exact format below, and
  paste the tagging rule and the keep / leave-out lists from this step into its prompt word
  for word (including: drop the reminder line, tag `[voice]` when there is no "Message sent
  at" reminder, keep only the quoted comment text from an artifact-comment relay, skip the
  trigger message), and the **drill-mark tagging** rule below, word for word;
- ask it to return only the turn numbers it wrote with their voice/typed tags, the pages
  read and the highest turn number, not the text itself.
Then check the file yourself before Step 3: the turn count, the tags, and a few turns spot-
checked against the chat. Tested on 27.09.26 with a 50-turn chat: every turn came back
verbatim. The helper's pages are not in your context afterwards, so in a wrap-up the Mini
Prompt's Step 2 has to page the chat itself (or ask the same helper, via SendMessage, for a
summary of the whole session, Claude's side included).

After each page, append Murat's turns to `/tmp/nc/murat_turns.txt` straight away (so a
compaction mid-recovery loses nothing), each turn tagged voice or typed:

```
### T<n> [voice]
<his exact words>
```

**How to tag:** a typed message always starts with a `<system-reminder>` line carrying its
timestamp ("Message sent at …"); a voice turn has no such line. That rule is reliable, so use
it, not the style of the text. Drop the reminder line itself; keep only his words. Voice and
typed are scored separately on the dashboard, because typed English has fewer slips and
mixing them would blur the trend.

**Drill marks (added 29.10.26).** Two drills can sit inside a practice chat, each wrapped in fixed
marks that Claude says at the start of a message:
- the **fixing slot**: "Fixing slot starts." … "Fixing slot ends." (fixing-slot skill);
- the **vocab drill** (the story loop of a vocab session): "Vocab drill starts." … "Vocab drill ends."
Every turn of Murat's that comes after a start mark and before its end mark gets an extra tag in
its header: `### T<n> [voice] [slot]` or `### T<n> [voice] [vocab-drill]`. Turns outside the marks get
no extra tag. A drill can happen more than once in a chat; tag each stretch. **If a start mark has
no end mark, or an end mark has no start, stop and ask Murat where the drill began or ended. Never
guess.** A chat with no marks needs no extra tags.
What the tags do: only the drilled items, and only in tagged turns, are kept out (the slot's
targets from the chunk counts; the vocab drill's practised words from the come-ups). Everything
else in a tagged turn is checked and counted as normal: grammar, interference, prepositions,
vocabulary, phrasal verbs, word counts. Uses of a drilled item outside the marks are real uses.

Copy his words verbatim, voice-transcript fillers and all (the script strips "uh/um",
repeats and "you know / I mean"). Keep:
- everything he typed or spoke himself, including short task requests.

Leave out:
- anything Claude said;
- third-party material he pasted or attached (podcast transcripts, articles, reading
  passages, vocabulary lists, the Mini Prompt), even when it sits inside one of his
  messages. Keep only his own sentences around it;
- the message that triggered this check.

If the chat included a vocab session, write its final agreed target words (the vocab-session
skill ends with a line **Practised words:** listing them) to
`/tmp/nc/drilled_words.txt`, one expression per line, spelled exactly as the `expr` in
`meta/vocab_tracker`, or, for a phrasal verb, exactly as its `word` in `meta/pv_tracker`.
Uses of those words **inside the vocab drill marks** (turns tagged `[vocab-drill]`) are practice, not
spontaneous come-ups, so vocab.py and pv.py skip them there; a use outside the marks is a real
come-up. `vt_apply.py` (Step 5) records every practised word as one review either way.

If the chat included a fixing slot, write the chunk ids from its **Drilled targets:** line (e.g.
`s2`, `c5`) to `/tmp/nc/slot_targets.txt`, one per line. chunks.py keeps those items out of the
counts in turns tagged `[slot]` only.
Include words from both phases (artifact quiz and story loop). If the session ran over two
chats (quiz in one, stories in the next), list the words in each chat's check.

If the chat is very long and you have to stop paging early, say so in the report
("covers turns 0–N of M"). Never present a partial check as the whole session.

**If `read_conversation` isn't available (added 30.09.26).** It happened on 29.09.26: the tool
answered "claude_ai server does not offer this tool here". Then:
- **The chat was never compacted** (you can see it from its very first message, with nothing
  summarised): write Murat's turns from your context, with the same format and rules as above,
  and say in the report that the turns came from context.
- **The chat was compacted, or you can't be sure**: don't check what's left. Stop and tell Murat
  plainly that the earlier part can't be read back here. Offer two ways on: he pastes or attaches
  the missing part (his own messages are enough for the check; the Mini Prompt also needs Claude's
  side), or he runs the check again after a short new practice stretch in this chat. A check of a
  partial chat must never be saved as the whole session.
- **No chat URL, so no chat id for the doc id**: use the first 8 characters of another id that is
  fixed for this chat (for example the id of an uploads folder, as on 29.09.26), name it in the
  report, and use the same id for any rerun in this chat.

## Step 3: Run the detectors

```bash
cd /tmp/nc && python3 detect.py murat_turns.txt candidates.json
python3 vocab.py murat_turns.txt meta/vocab_tracker.json olp vocab_candidates.json drilled_words.txt
python3 pv.py murat_turns.txt meta/pv_tracker.json pv_candidates.json drilled_words.txt
python3 chunks.py find murat_turns.txt meta/chunks.json chunk_candidates.json slot_targets.txt
```

`chunks.py find` (added 12.10.26) prints a CHUNK REVIEW LIST for every open chunk and slice (c1–c5 and s1–s4 since 12.10.26; s5–s7 since 29.10.26):
index, item id, mode, turn, the script's suggestion (`correct`, `WRONG`, or `decide` when it can't
tell), the matched words and the sentence. If it prints `NOT COUNTED (no finder yet ...)`, Murat opened
a chunk the script can't count yet: the other open chunks are still counted; say in the report
("chunk X isn't counted yet") and never estimate its numbers by eye. If there was a fixing slot, it
also prints a SLOT LIST: the drilled targets inside the slot, kept out of the counts. Use it only to
check the slot's **Slot result:** line and repeat that line in the report; never add these uses to
the chunks block. If it prints `SLOT: targets given but no turn is tagged [slot]`, the tagging went
wrong: fix murat_turns.txt (or ask Murat) before going on.

`detect.py` prints the word count (voice and typed) and a REVIEW LIST of grammar candidates: index, kind
(`use` = a structure was used, `error` = an error signature), concept id, match, sentence.
High-volume, low-risk concepts (basic connectors, "will", and the A1/A2 basics: present
simple, past simple, can, there is/are) are auto-accepted and not listed. Their errors still
surface through the `err_*` detectors (agreement, do-support and so on).

`vocab.py` prints the CEFR level mix, the lexical diversity (MTLD) for voice and typed, and a VOCAB REVIEW LIST: `comeup` lines (an expression
from his vocab list appeared) and `advanced` lines (first use of each B2+ word), then an
OFF-LIST REVIEW: every word of 5+ letters that is on neither CEFR list, with its count, its
everyday-English frequency (Zipf, from wordfreq) and a suggested level from that frequency.

`pv.py` prints a PHRASAL VERB REVIEW LIST: every candidate, one line per phrasal verb per
sentence, with its source (`tracker` = matched a tracker expression, `particle` = spaCy marked
a particle, split forms like "turn it off" included, `prep` = verb + adverb-like preposition)
and flags (`tracker` / `NEW`, `split`, `drilled`). `drilled` is set only inside the vocab drill
marks; those uses are left out of every count automatically, and uses outside the marks count.

## Step 3b: Turkish-interference passes (added 27.09.26)

Murat's goal here is direct English thinking: catching where Turkish shaped a word, a phrase or a
sentence. No script can find new interference patterns, so this step uses two independent
readers instead of one. In the 27.09 pilot a single pass missed about a third of what Murat then
confirmed; the union of two blind passes is the method.

Launch **two general-purpose subagents in parallel** (one message, two Agent calls). Give each
exactly this task, with `A` / `B` as its letter:

> Read /tmp/nc/intf_instructions.md fully and follow it exactly. Pattern list:
> /tmp/nc/meta/interference.json. Turns file: /tmp/nc/murat_turns.txt. Write your output to
> /tmp/nc/intf_A.json. Do not read any other file in /tmp/nc.

They must not see each other's output. Before merging, make sure **both** passes finished: each
subagent's reply gives its counts, and `/tmp/nc/intf_A.json` and `/tmp/nc/intf_B.json` must both
exist. If a pass failed, ran out of time or wrote nothing, run that one pass again with the same
task; never merge one pass on its own. `intf.py merge` also refuses (prints `STOP`) when a file is
missing or broken, or when one pass found nothing while the other found 5 or more. Then merge:

```bash
cd /tmp/nc && python3 intf.py merge intf_A.json intf_B.json meta/interference.json intf_merged.json
```

It prints both counts, the union, how many items both passes found, and a REVIEW LIST of the
items that need your eye (found by one pass only, unknown pattern keys, or the two passes chose
different keys), followed by the upgrade suggestions.

## Step 4: Verify every line of all three lists

**Grammar list.** For each index decide:
- **correct** (default for `use`): the structure really is there and used correctly. Do nothing.
- **drop**: a false positive. The parser misread it (a gerund read as a continuous tense,
  "for a while" read as a connector, "time to go" read as a relative clause), he is
  quoting someone else's text, or he is talking *about* a word ("did I use run through
  correctly?").
- **error**: a `use` candidate that is actually wrong. Write a short fix. Example:
  "it's been started" → "it started" (start isn't passive here).
- **fix**: every real error needs a one-line fix, with no exceptions (Murat's rule, 28.09.26:
  an error without a fix tells him nothing on the dashboard). That covers detector-flagged
  `error` lines, `use` lines you mark as errors, relabelled lines and every `extra`. Write it as
  "wrong part -> right part" ("fits more natural -> fits more naturally"), not a whole
  rewritten sentence, so he can see exactly what changed. `session.py` stops and lists any
  error that still has no fix. If a flagged error isn't really an error, **drop** it.
- **C2 lines** (`c2_*`) need the strictest check. Keep one only if the structure is really
  there and complete: "Should I use it?" is a question, not inversion; a rambling sentence
  that the parser read as three nested clauses is not stacked subordination. When in doubt,
  drop it. A missing C2 is honest; a false one inflates his range.
- **relabel**: move to another concept id. The known case is "in the meantime" used to
  mean "by the way" (Turkish "bu arada"). Relabel to `err_in_the_meantime`. It is only
  correct when it means "during that time". Its fix defaults to "'in the meantime' used for
  'by the way' -> by the way"; put a different one in `fix` when "anyway", "also" or "now"
  fits the sentence better.
- **caught** (added 01.10.26, Murat's rule): an error he corrects **right away**, in the same
  breath, counts as half an error. Two signs: he says the wrong form and then the right one
  ("they are trying to downplaying, they are trying to downplay"), or he flags it at once
  ("In the meantime, sorry, by the way"; "in the meantime, sorry."). It is still logged as an
  error with its fix, plus `"caught"`. Three cases stay full errors: the correction is still
  wrong ("about to called off… call off"), he changed a right form into a wrong one ("I went
  through it… I went it through"), or the "sorry" is about another word in the sentence ("in the
  meantime, I think we will hire, sorry, rent a car": the "in the meantime" is not caught). List
  detector indexes in `"caught": [..]` and set `"caught": true` inside an `extra`. `session.py`
  counts each caught error as 0.5 in every total and rate, and stores `errors_caught`.
- **B2–C2 expansion lines** (added 26.09.26, from the English Grammar Profile): the 31
  concepts in `DETECTORS_V3` are pattern-based and mostly precise, but check these known traps:
  a perfect passive of a verb that isn't passive here ("it's been started", "the journey has
  been started") is an **error**, not a correct use; "due to" meaning "because of" is not
  `b2_be_about_due_to`; "the problem is" + a plain noun ("the problem is the data") is not
  `b2_the_thing_is` (it needs a clause after it); "for which is dedicated" (preposition +
  which with no subject) is an error, not `b2_preposition_relative`. A structure used with an
  unrelated slip elsewhere in the sentence still counts as correct for that structure.
- **Batch 2 lines** (`DETECTORS_V4`, added 26.09.26) lean on the parser, so expect more
  drops (about 1 in 4 in the back-test). `b2_phrasal_prepositional_verb` and
  `c1_split_phrasal_pronoun` fire once per verb per session: keep them only when the phrasal
  verb itself is real and right ("come up with", "figure it out"); **drop** misuses ("scare
  her up", "shook me out", "put it out on" for "take it out on", "lean towards on") and
  adjunct prepositions that aren't part of the verb ("pay off at the end", "slip up for some
  reason"); log the misuse itself as a grammar `extra` (`err_collocation`) with its fix.
  `b2_stranded_preposition` needs a real relative or question ("a topic to talk about",
  "something you're born with"); drop half-finished sentences and quoted words ("tempt someone
  to"). Drop a negative question that is garbled. "It's + adjective + that" belongs to
  `b2_it_adjective_that`; if `c1_cleft_sentences` fired on the same sentence, drop the cleft
  line (a real cleft emphasises a noun: "it was Luke who…").

Then read Murat's turns once for **clear errors the detector missed** and add them as
`extra`, each with the sentence, a fix and an `err_*` id: `err_preposition`,
`err_subject_verb_agreement`, `err_habitual_past` ("we were hanging out" for a habit),
`err_causative_to`, `err_collocation`, `err_other`. Give each extra the `mode` of its turn
(`voice` or `typed`). Add only errors you are sure about. The pass is capped at clear
mistakes, not style preferences.

**Chunk list (added 12.10.26).** The definitions are in `meta/chunks` (each item's `counts`,
`correct`, `wrong` and `left_out`); judge every line against them, not against general taste.
For each index:
- **keep** (default): the suggestion is right.
- **flip**: the use is real but the suggestion is wrong (marked correct but it's a mistake, or the
  other way round).
- **set**: the suggestion is `decide`: give `true` (correct) or `false` (wrong).
- **drop**: not a real use under the definitions: quoting a text, talking *about* the chunk ("is
  it add to or into?"), repeating a sentence Claude just modelled, a "left out" case, or a
  transcript you can't trust ("to" or "into"? drop it, don't guess).
- **caught**: he corrected it straight away; it counts as half, as elsewhere.
- **extra**: a clear use of an open chunk the script missed, with item, turn, mode, sentence and
  `ok`. Only ones you are sure about.
A wrong chunk use is usually also a grammar error or an interference item; log it there as
usual too. The chunk count is a separate measure, not a replacement.
Write `/tmp/nc/chunk_verdicts.json`: `{"drop": [..], "flip": [..], "set": {"index": true},
"caught": [..], "extra": [{"item": "c1", "turn": "T7", "mode": "voice", "sentence": "...", "ok": false}]}`.

**Vocab list.** Put an index in `vocab_drop` when:
- he is quoting a list, a reading text or Claude ("let's swap these ones: dwell, …");
- he is talking about the word rather than using it ("did I use run through correctly?");
- the pattern matched loosely and the item isn't really there ("build up a tracker for it"
  is not "up for it"; "come to an end" is not "come to" = regain consciousness);
- a B2+ word only appears because he is naming a word from a text.
A come-up used with a small error still counts as a come-up (it's a real attempt). Note the
error in the grammar list instead.
Put junk off-list words (project jargon like "tracker", "vocab", misspeaks, words he only
mentioned) in `offlist_drop`.

**Off-list levels (added 26.09.26).** The CEFR lists have about 8,000 words, so real,
often advanced words Murat uses ("ubiquitous", "hesitancy", "nuance") are on neither list.
Leaving them ungraded undercounts his B2+ share. For **every** off-list word you keep, write
its level in `offlist_levels`. Start from the frequency suggestion, then correct it by how a
learner meets the word, not raw frequency:
- simple but not in the lists (ordinals, obvious derivations): low. "fourth" A1, "reopen" B1;
- informal or slang words that are rare in written data: judge by use. "knackered" C1;
- rare technical or coined forms: high. "frictional", "effortful" C2;
- figurative uses count at their higher level ("bandwidth" for mental capacity: C1).
Key each entry by the word exactly as the OFF-LIST REVIEW prints it. A kept word you leave
out falls back to the frequency suggestion, so cover them all.
These levels are shown on the dashboard as "est." so Murat can always tell them from the
official lists. Judge carefully; the main question is whether a word is B2+ or below.

**Phrasal verb list (added 26.09.26).** For each index decide:
- **keep** (default): Murat really used that phrasal verb, correctly or not. An attempt with a
  small error still counts (it's a real use); log the error as a grammar `extra`
  (`err_collocation`) with its fix, so it shows in the errors panel.
- **pv_drop**: not a phrasal verb here. Literal verb + preposition ("walked down the street",
  "went through the door" is literal only if it means a physical door), he is quoting a text,
  a list or Claude, or talking *about* the word ("is 'come up' on the tracker?"). Talking about
  the tracker's own vocabulary ("come-up") is not a use of "come up".
- **pv_relabel**: the right entry is a different tracker row: a past-tense duplicate row
  ("took back" → "take back"), a longer or shorter form of the same headword ("cram into" →
  "cram in", "get back to you" → "get back to (someone)"). Use the tracker's exact spelling.
  A NEW word stays new only if no tracker row is the same phrasal verb.
- **pv_extra**: a clear phrasal verb the script missed (usually prepositional verbs not on the
  tracker, like "rely on"), with its turn, mode and sentence. Only ones you are sure about.
- **No notes.** Since 27.09.26 Murat wants no notes on the tracker: leave `pv_notes` out of
  verdicts.json. A wrong particle or word order ("pick up her") goes into the grammar `extra`
  list as an error instead.
If a chunk of text is genuinely ambiguous (his own words or something he pasted?), ask him
before counting it.

**Interference list (added 27.09.26).** Items found by both passes are accepted. For each line on
the REVIEW LIST:
- **keep** (default): one-pass items are usually real. Murat confirmed every disputed type in the
  pilot, including "how to say" fillers, voice article drops, "from the beginning"
  for "since", and "for" from için.
- **drop**: only when it is clearly not interference: natural English, he is quoting someone or
  talking about a word, a transcription artefact, or no concrete Turkish source. Drop any "let's say" item (Murat, 29.09.26: no longer
  counted; the pattern `lets_say_filler` now means "how to say" / "how can I say" only). All eight
  sessions to 28.09 were recounted on 29.09 without "let's say" (82 items removed).
- **repeat** (Murat's rule, 01.10.26; replaces the 27.09 "drop game moves" rule): a stock reply
  repeated inside a game or drill, e.g. "that's true" for "that's right" (doğru) each time he
  confirms Claude's guess in Taboo, **is** interference, but it counts **once per session**. Keep the
  first one and put every later repeat of the same pattern in that game in `"repeat": [..]`; they
  are stored with `counted: false`. Repeats outside a game (a filler he uses all session, such as
  "in the meantime" or "that's because") are separate slips and each one counts.
- **caught** (Murat's rule, 01.10.26): same rule as for grammar. If he corrects the item right away
  or flags it at once ("In the meantime, sorry, by the way"), keep it and list it in
  `"caught": [..]`: it counts as half. `intf.py` prints a SELF-CORRECTION CHECK of likely
  candidates; check **every** line of it, and any other item where you see a correction.
  The same moment is usually also a grammar error (`err_in_the_meantime`): mark it caught in both lists.
- **pattern**: if a pass used an unknown key or a `new:` label, map it to an existing key when one
  fits. Add a **new pattern** only for something that recurs (2+ times) or is clearly distinct;
  otherwise use the matching `other_*` key. A new pattern needs `{key, label, turkish, type, fix}`,
  with a label Murat will understand on the dashboard.
- **upgrade_drop**: upgrade suggestions that are only taste, not a clearly more natural choice.
Write `/tmp/nc/intf_verdicts.json`: `{"drop": [..], "pattern": {"index": "key"}, "upgrade_drop": [..],
"new_patterns": [..], "impact": {"index": "m"}, "repeat": [..], "caught": [..]}` (empty lists/objects are fine; `impact` only for overrides).

**Impact of every mistake (added 30.09.26).** Murat's point: many mistakes are small slips made
under the load of speaking, but some really matter. Give every grammar error (detector `error`
lines, `use` lines you mark as errors, relabelled lines and every `extra`) one label:
- **m, changes the meaning**: the listener may understand something else, or not follow. "went
  straight over our heads" for "slipped our minds", "should have missed" for "must have missed",
  "in the meantime" for "by the way", "warned them off" for "warned them", "that's because" for
  "that's why" (cause and result swap).
- **f, sounds foreign**: the meaning is clear, but a native speaker wouldn't say it. Mostly
  Turkish habits: "mention about", "ask the question to her", "important at my side", "let us to
  use", "married with".
- **s, slip**: he knows the rule and gets it right most of the time; it broke under pressure.
  "club seats tends", "more strong", "a genuine relieve", "why ancient people build".
Decide yourself and never ask Murat (his decision, 30.09.26: he relies on these calls). When
torn between two labels, pick the more serious one only if a listener could really misread
him. For a structure on the grammar list, the session's own counts help: a structure he used
correctly 80%+ of the time that session is usually a slip. `session.py` fills in the types whose
label never changes (`DEFAULT_IMPACT`: "in the meantime" m, prepositions f, agreement and the
other form slips s) and stops, listing them, if any other error has no label.
Turkish-interference items get their label automatically from the pattern and its type
(`intf.py`: "by the way" and "that's why" m, false friends m, articles and dropped pronouns s,
everything else f). Override one only when that item is clearly different, in
`intf_verdicts.json` as `"impact": {"index": "m"}`.

Write `/tmp/nc/verdicts.json`:

```json
{"drop": [12, 40],
 "error": {"57": "it's been started -> it started"},
 "fix": {"3": "despite + clause -> even though ...", "8": "'in the meantime' used for 'by the way' -> anyway"},
 "relabel": {"8": "err_in_the_meantime"},
 "impact": {"57": "f", "3": "f"},
 "caught": [8],
 "extra": [{"concept": "err_collocation", "turn": "T56",
            "mode": "voice", "sentence": "the lesson time went straight over our heads",
            "fix": "went straight over our heads -> slipped our minds", "impact": "m"}],
 "vocab_drop": [1, 2, 23],
 "offlist_drop": ["tracker", "vocab"],
 "offlist_levels": {"ubiquitous": "C2", "fourth": "A1", "knackered": "C1"},
 "pv_drop": [4],
 "pv_relabel": {"9": "cram in"},
 "pv_extra": [{"word": "rely on", "turn": "T31", "mode": "voice",
               "sentence": "we can rely on the new system"}]}
```

## Step 5: Build the session document

```bash
cd /tmp/nc && python3 session.py candidates.json verdicts.json <DD.MM.YYYY today> "<chat title>" s_<YYYYMMDD>_<first 8 chars of chat id> session_doc.json vocab_candidates.json pv_candidates.json meta/pv_tracker.json
python3 pv_apply.py meta/pv_tracker.json session_doc.json <DD.MM.YYYY today> pv_tracker_out.json
python3 intf.py apply intf_merged.json intf_verdicts.json meta/interference.json session_doc.json meta_interference_out.json
python3 vt_apply.py meta/vocab_tracker.json session_doc.json <DD.MM.YYYY today> vocab_tracker_out.json drilled_words.txt pv_tracker_out.json
python3 lex_apply.py meta/lexicon.json vocab_candidates.json session_doc.json <doc_id> lexicon_out.json
python3 chunks.py apply chunk_candidates.json chunk_verdicts.json session_doc.json
DOC_ID=<doc_id> python3 chunks.py rolling sessions session_doc.json meta/chunks.json
python3 preps.py run murat_turns.txt session_doc.json meta/prep_watch.json prep_watch_out.json <doc_id>
```

`preps.py run` (added 16.10.26) must come after `intf.py apply` and `session.py`: it reads this
check's own preposition slips from `session_doc.json`, so it decides nothing itself. It writes the
`preps` block into `session_doc.json` and the updated watch list to `prep_watch_out.json`, and prints
a few `PREPS:` lines for the report (overall, watch list, voice and typed, weakest group, words that
joined the list). Running it twice in the same chat changes nothing twice. If it prints
`PREPS SKIPPED: …`, it has changed nothing and written no `prep_watch_out.json`: carry on with the
check, leave `meta/prep_watch` out of the save, and say in one line of the report that the
preposition figures are missing today. Never fix or rerun it by hand beyond one retry, and never
count prepositions by eye instead.

`chunks.py apply` (added 12.10.26) writes the `chunks` block into `session_doc.json` (per open item:
voice and typed uses, correct, wrong, accuracy, and every counted use). It stops if a `decide`
line still has no verdict. `chunks.py rolling` pools the voice uses across all sessions and prints,
per open chunk, the last 12 uses, how many sessions they span, the accuracy, and `SUGGEST SETTLED`
when the rule is met. It only suggests: tell Murat in the report; he decides.

`lex_apply.py` (added 29.09.26) keeps the running count of **unique words**: every different
word Murat has used since 29.09.26, counted by base form (go, went and gone are one word; names,
numbers and fillers are left out). It adds this session's new words to `meta/lexicon` and writes
`vocab.unique` = `{session, new, total}` into the session doc. Running it twice in the same chat
changes nothing twice. If `meta/lexicon.json` doesn't exist yet (first run), it starts a new one.

`vt_apply.py` (added 27.09.26) adds the day to every vocab-list word in the session's verified
`vocab.comeups`, records each drilled word as one review (`practice.count` +1, `practice.last`),
and prints the changes, stage-ups and counts. A drilled phrasal verb is recorded as a review on
its row in `pv_tracker_out.json` (run it after `pv_apply.py`, which writes that file). It never
adds words and never touches `mastered`.
If it prints `CHECK:` for a drilled word, the spelling in drilled_words.txt doesn't match the
list: fix the spelling and rerun (vocab.py needs the same exact spelling to skip it).

`intf.py apply` adds an `interference` block to the session (per 100 words, voice and typed
separately, every item with its pattern and Turkish source, the upgrade suggestions). A voice
"missing article" counts only when that pattern occurs twice or more in voice that session, since
the transcriber can drop small words. If you added new patterns it also writes
`meta_interference_out.json`.

`session.py` adds a `pv` block to the session (words, instances, distinct, per_1000, by_mode,
items, comeups, new_words), an `impact` label on every error and the session's `impact` counts
(`{m, f, s}`). If it prints `STOP: … error(s) have no fix` or `STOP: … have no impact label`, it
has written nothing: add what it lists to verdicts.json and rerun it before the other scripts.
`pv_apply.py` adds today's date to every tracker word that
came up, adds first-time words, and prints the changes and any stage-ups
(e.g. "figure out -> Activated"). One date per word per day, so a second run in the same chat
changes nothing twice.

Then link any new phrasal verbs to the native core list (the Native core panel counts
variants: "went on with" counts for "go on"):

```bash
python3 phave_link.py meta/phave.json session_doc.json phave_out.json
```

It writes `phave_out.json` only when a new word is a variant of one of the 150 core verbs; the
exceptions that are different verbs ("get up to", "get in touch with", "hold on to") never link.

If you used a grammar concept id that isn't in `meta/registry`, add
`"<id>": ["<label>", "<level or null>"]` to its `concepts` in a copy, `/tmp/nc/registry_out.json`.

Use the date of the chat's practice day (normally today). The doc id is fixed per chat, so
running the check twice in the same chat replaces that session instead of adding a duplicate.
Whether the session doc already exists is in `index.json` from Step 1.

## Step 6: Write the day's report and the Overview brief (added 30.09.26)

Both are written before the save, so they go into the same single approval.

**0. Sentences with a slip (added 28.10.26).** Murat asked for an errors-per-sentence figure in
the report only, not on the dashboard: it is closer to how speaking feels to him than errors per
100 words. Write this script to `/tmp/nc/sentences.py` exactly as below (it reuses detect.py's
cleaning and sentence split) and run it after Step 5's scripts, before writing the report:

```bash
cat > /tmp/nc/sentences.py <<'EOF'
# sentences.py (added 28.10.26): share of voice sentences with at least one counted error.
# usage: python3 sentences.py murat_turns.txt session_doc.json sessions
import sys, re, json, glob, difflib
from detect import clean, load_turns, nlp

def norm(t): return re.sub(r"[^a-z' ]", "", clean(t).lower()).split()

turns_p, doc_p, sess_dir = sys.argv[1], sys.argv[2], sys.argv[3]
sents = []
for turn, raw, mode in load_turns(turns_p):
    if mode != "voice": continue
    for s in nlp(clean(raw)).sents:
        if len(s) >= 3: sents.append((turn, norm(s.text)))
doc = json.load(open(doc_p, encoding="utf-8"))
hit, unmatched, rank = {}, [], {"m": 0, "f": 1, "s": 2}
for e in doc.get("errors", []):
    if e.get("mode", "voice") != "voice": continue
    q = norm(e.get("quote", ""))
    if not q: continue
    qs, best, score = " ".join(q), None, 0.0
    for i, (_, w) in enumerate(sents):
        ws = " ".join(w)
        sc = 1.0 if (qs in ws or (ws and ws in qs)) else difflib.SequenceMatcher(None, q, w).ratio()
        if sc > score: best, score = i, sc
    if best is None or score < 0.6: unmatched.append(e.get("quote", "")[:80]); continue
    imp = e.get("impact", "s")
    if best not in hit or rank.get(imp, 2) < rank.get(hit[best], 2): hit[best] = imp
n, k = len(sents), len(hit) + len(unmatched)
res = {"voice": n, "with_error": k, "pct": round(100 * k / n, 1) if n else 0.0,
       "with_m": sum(1 for v in hit.values() if v == "m"), "unmatched": len(unmatched)}
doc["sentences"] = res
json.dump(doc, open(doc_p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
prev = None
for f in sorted(glob.glob(f"{sess_dir}/*.json")):
    d = json.load(open(f, encoding="utf-8")); d = d.get("data", d)
    if d.get("sentences") and d.get("date") != doc.get("date"):
        prev = f'{d["sentences"]["pct"]}% on {d["date"][:5]}'
print(f"SENTENCES: {k} of {n} voice sentences had a slip ({res['pct']}%), {res['with_m']} with a meaning change; previous: {prev or 'none yet'}")
for u in unmatched: print("  UNMATCHED (counted as its own sentence):", u)
EOF
cd /tmp/nc && python3 sentences.py murat_turns.txt session_doc.json sessions
```

It counts voice sentences of three or more tokens (the same split detect.py uses), matches each
voice error's quote to its sentence, and counts each sentence once however many errors it holds.
An error it can't place is counted as one more sentence with a slip and listed as UNMATCHED. It
writes a `sentences` field into `session_doc.json`, so the figure is saved with the session in
Step 7 and the next check can compare with it. Sessions before 28.10.26 have no figure, and it
can't be backfilled (only error quotes are stored, not transcripts). Say "previous: none yet"
plainly until there is one. No voice turns (a typed-only chat): leave the line out.

**1. The report** (`/tmp/nc/report.md`). Write the text report now, in the fixed format below
(Murat asked to keep it that way, 29.09.26). The same text is saved with the session (the
Overview tab shows it as "Session report") and is what you give him in Step 8. Take every number
from `session_doc.json` and the script outputs, never estimate. Quote only Murat's words.

```
Naturalness check, <Ddd DD.MM>: <words> words (voice <n>, typed <n>), <observations> observations, <errors> errors.

- **Voice: <x.xx>** errors per 100 words (<prev> on <prev date>).
- **Typed: <x.xx>** per 100 (<prev> on <prev date>). <if under ~500 words: say it is a small sample and why>
- **Sentences with a slip: <k> of <n> (<pct>%)** in voice (<prev>), <with_m> of them with a meaning change. Read the trend, not the exact figure: the count depends on how the transcript is punctuated.
- <one line on anything that changes how to read the numbers, e.g. a method change; leave out if none>
- <only if there was a fixing slot: "**Fixing slot:** <the Slot result line, e.g. I've already 6/6 · I still have 3/5>. Kept out of the chunk counts; everything else in it is counted.">

## Errors
**<the top recurring error>: <n> times.** <one or two sentences: what changed, with his own quotes>
Mistakes by impact: <m> change the meaning, <f> sound foreign, <s> slips.
<if errors_caught: "You caught <n> of them yourself, right away (counted as half each)." with one quote>

### <Group> (<n>)
- "<his words>" → <fix>
   (groups by type, recurring first: e.g. Prepositions, Word choice and collocation, Grammar and
    other; up to about 10 lines each; a line may carry one short honest note, e.g. where Claude's
    live feedback was wrong)

## Strong B2+ grammar
- "<quote>"   (3–5 lines)

## Phrasal verbs
**1 per <N> words**, against the native rate of 1 per 192. <how it compares>. You used <uses> phrasal verbs, <distinct> different ones<, and the drilled words used inside the vocab drill aren't counted>. <n> of them are on the tracker.
- **New:** ...
- **Moved up to Activated:** ...
- **Moved up to In Progress:** ...
- <one line on precision: misused ones, quoted>

## Vocabulary
- **B2+ share: <x.x>%** (<prev> on <prev date>). Counting only words on the official CEFR lists, it's <x.x>% (<prev>).
- **Notable words:** ...
- **<n> words from your list** came up on their own. <the best one, quoted; first-ever uses>
- **Lexical diversity (MTLD):** <voice> in voice (<prev>) and <typed> typed (<note if small>).
- **Unique words:** <session> today, <new> new, <total> in total.
- **Vocab tracker:** <stage-ups; reviews recorded if there was a vocab session>

## Turkish interference
**<x.xx> per 100 words** in voice (<prev>) and <x.xx> typed (<prev>).

### Top patterns in voice
- <pattern>: <n> ("<quote>" → <fix>)   (top 3–4)

### New patterns added
- ...   (only if any)

### Useful upgrades
- "<quote>" → <suggestion>   (2–3)

### Prepositions
- **<x>%** of <n> uses (voice <v>%, typed <t>%); watch list **<w>%** of <m>. Weakest group: <group> <g>%.
- Joined the watch list: <words, or "none">.   (from the `PREPS:` lines; "missing today" if PREPS SKIPPED)

## Chunks
- **<focus item title>:** <n> uses in voice today, <c> correct. Last 12: <acc>% over <s> sessions<, SUGGEST SETTLED>.
   (one line per focus item; "no uses today" when none; quote one wrong use with its fix)
- **Also tracked:** <title> <c>/<n>, <title> <c>/<n>, ... (only items used today, one line; then any
   SUGGEST SETTLED among them, with its last-12 figure)
```

Headings must stay exactly `## Errors`, `## Strong B2+ grammar`, `## Phrasal verbs`, `## Vocabulary`,
`## Turkish interference` and (since 12.10.26) `## Chunks` (the page lays the report out by them; `overview.py` checks the first five).
Sub-groups use `###`, lines use `- `, bold uses `**`. Nothing else.

**2. The numbers for the brief.**

```bash
cd /tmp/nc && python3 overview.py stats sessions session_doc.json <doc_id>
```

It prints, word-weighted and with this chat's session counted once: today vs the session
before; this week (Monday to Sunday) vs last week; the last 3 sessions vs the first 3; all
sessions; and mistakes by impact (overall and per session). Every number you put in the brief
comes from this output or from `session_doc.json`.

**3. The brief** (`/tmp/nc/overview_draft.json`). Rewrite it from scratch every time, from all the
sessions, never by editing the old one. It is an executive brief, not a summary: a story behind
the numbers, frank both ways, few numbers, short sentences, Murat's own quotes with the fix.
Honesty rules: every number from the stats or the session doc; say so when a method change could
explain a trend; call a typed sample under ~500 words small; no praise the numbers don't support,
and no gloom they don't support either.

```json
{"headline": "Your English is getting bigger. It isn't getting cleaner yet.",
 "intro": "2-3 sentences: the story in plain words, and the job for the next sessions.",
 "periods": {
  "today": {"sub": "Tue 29.09 · 6,397 words", "verdict": "Ambitious day, sloppy edges.",
            "scores": [{"label": "Errors per 100 words", "value": "1.11", "was": "0.97", "move": "worse"},
                       {"label": "Phrasal verbs", "value": "1 per 42", "move": "best", "tag": "Best yet"}],
            "points": [{"kind": "good", "text": "First time you used \"egregious\" without being asked."},
                       {"kind": "bad", "text": "\"Mention about\" 4 times.", "said": "I mentioned about Spain trip", "say": "I mentioned the Spain trip"}],
            "note": "optional one line, e.g. a method change"},
  "week":  {"sub": "Mon 28 – Tue 29.09 · vs last week", "verdict": "More range, less accuracy.", "scores": [], "points": []},
  "start": {"sub": "9 sessions · 18–29.09", "verdict": "Range up by 60%. Accuracy hasn't moved.", "scores": [], "points": [],
            "note": "Scores compare your last 3 sessions with your first 3."}},
 "priorities": [{"title": "Say \"by the way\" first time", "impact": "m",
                 "text": "You already catch it. Now stop it before it starts.",
                 "said": "In the meantime,", "say": "By the way,", "rest": "this team doesn't report to me."}],
 "impact_notes": {"latest": "1-2 sentences on the latest session's mix of the three kinds",
                  "all": "1-2 sentences on all sessions",
                  "trend": "1-2 sentences on how the shares move over the sessions"},
 "best_moments": [{"title": "First unprompted \"egregious\"", "date": "29.09", "kind": "word",
                   "quote": "there is an egregious mistake in our budget figures"}]}
```

- **Scores**: 2–4 per period, chosen to fit that period's story (they change from day to day).
  `move` is `better`, `worse`, `same`, `best` or `worst` (the page colours it); `was` is the
  comparison value; `tag` replaces the Better / Worse word when useful ("Best yet", "Fix first").
- **Points**: 2–5 per period, at least one `good` and one `bad`, at most 40 words each. Put his
  quote in `said` and the fix in `say` rather than in the text.
- **Priorities**: exactly 3, the things that would help most next time, each with its impact
  label (lead with `m` ones) and one real sentence of his.
- **Best moments**: up to 8 from the last three sessions: stage-ups, first unprompted list
  words, strong B2+ structures, self-corrections. Each with its date and a quote or a short line
  (`sub`).

Then check both and put them in place:

```bash
cd /tmp/nc && python3 overview.py finish sessions session_doc.json <doc_id> overview_draft.json report.md overview_out.json
```

If it prints `STOP`, it has written nothing: fix what it lists and rerun. On success it adds the
report to `session_doc.json` (field `report`) and writes `overview_out.json` for `meta/overview`.
Run it after every script that edits `session_doc.json` (`intf.py apply`, `lex_apply.py`, `sentences.py`), so the
report and the brief see the final numbers.

## Step 7: Write it to the dashboard, in one save

Stage every file this check changed, in one command (a `?` file is skipped when a step didn't
write it):

```bash
cd /tmp/nc && python3 ledger.py stage /tmp/nc --session <doc_id> \
  sessions/<doc_id>=session_doc.json meta/pv_tracker=pv_tracker_out.json \
  meta/vocab_tracker=vocab_tracker_out.json meta/lexicon=lexicon_out.json meta/overview=overview_out.json \
  "meta/interference=meta_interference_out.json?" "meta/phave=phave_out.json?" \
  "meta/registry=registry_out.json?" "meta/prep_watch=prep_watch_out.json?"
```

It prints each list's rows before and after, then `PUBLISH:` with the files to send. Then follow
"Saving" in "The ledger's files": check the version id, publish those files in **one** publish
(Murat approves once), confirm the sizes.

If it prints `REFUSED`, nothing is staged and nothing is saved: a list would lose a row, a row would
lose a date or a review, or a file is broken. Tell Murat exactly what it lists and stop; never edit
the output files by hand to get past it. If the version changed before publishing (Murat may have
added a word, or a vocab session recorded reviews), nothing was saved: read the changed files again,
take a new snapshot, rerun the script that builds each one (`pv_apply.py` then `vt_apply.py` for the
trackers, `phave_link.py` for `meta/phave`, `lex_apply.py` for `meta/lexicon`, `overview.py finish`
for `meta/overview`, `preps.py run` for `meta/prep_watch`), stage and publish again. Never split the
save into several publishes to get round a conflict.

Never write the tracker .docx or a vocab .docx into the Project; the ledger is the only home.

## Step 8: Report

**Text chat:** give Murat the report from Step 6 (`report.md`) as it is, then one line with the
Overview's headline and the dashboard link ("the Overview tab has the full brief"). What each
part of the report holds:
1. The opening lines: words analyzed, observations, errors, and errors per 100 words **for voice and
   typed separately** (from `by_mode`), each with its change from the previous session (the doc
   before this one in `/tmp/nc/sessions/`). If one mode has under ~500 words, say its rate is based
   on a small sample. Then the share of voice sentences with a slip, from the `SENTENCES:` line.
2. The errors, grouped by type, each with Murat's quote and the fix. Lead with anything
   recurring (the dashboard's errors panel, "All sessions" view, shows what repeats and
   what is still active).
3. 3–5 strong B2+ grammar uses, quoted.
4. Phrasal verbs: density first ("1 per N words, against the native 1 per 192"), uses and
   distinct items, then tracker come-ups, new words and stage-ups from `pv_apply.py`.
5. Vocabulary: B2+ word share and its change (it includes estimated off-list levels; give
   the CEFR-list-only figure too, `b2plus_share_list`), a few notable B2+/C1 words he used, and the
   vocab-list come-ups (spontaneous uses of words from his list, with a quote for the most
   interesting one or two).
   Then lexical diversity: MTLD for voice (and typed if it has 100+ words), with the change from
   the previous session's same mode. One line; it's a trend, not a grade.
   Then unique words (from `lex_apply.py`): different words this session, how many were new, and
   the running total. One line.
   Then the vocab tracker (from `vt_apply.py`): words used unprompted today, stage-ups (e.g.
   "Articulate -> In Progress"), and the words and phrasal verbs recorded as reviewed if there
   was a vocab session. Phrasal verbs from the study list are reported under point 4 with the
   other phrasal verbs.
6. Naturalness (Turkish interference): interference per 100 words, voice and typed, with the change
   from the previous session's same mode; the top 3 patterns this session, each with one quote and
   its fix; any pattern that is new; two or three of the most useful upgrade suggestions. Lead with
   a pattern that is still recurring across sessions (the Naturalness tab's "All sessions" view).
   Then prepositions (added 16.10.26), from the `PREPS:` lines: overall and watch-list accuracy with
   voice and typed, the weakest group, and any word that joined the watch list. Two lines at most.
7. Chunks (added 12.10.26): one line per **focus** item from `chunks.py rolling` (today's voice uses
   and how many were correct, the last-12 accuracy and how many sessions it spans), one line for the
   other tracked items that came up today, and every `SUGGEST SETTLED`, focus or not (Murat
   confirms; never change `meta/chunks` yourself). A rare chunk with no uses today is normal: say
   "no uses today", not "fixed". Chunk 3 is a rough count: say so if you quote its figure.
8. The dashboard link for the full view (the Phrasal verbs tab shows the whole tracker, the
   Naturalness tab the interference patterns, the Vocabulary tab the vocab tracker).

**Voice mode:** the report and the brief are still written and saved in full (Step 6); only what
you say is short. Keep it short and spoken. Give the error rate, the share of sentences with a slip, the top two error types with
one example each, one good structure, the phrasal verb density, the interference rate with the
top pattern, the watch-list preposition accuracy, one vocab-list come-up if there was one, and the open chunks in one sentence. Say the
rest is on the dashboard. Section 0's voice rules apply: no recap of the conversation.

Quote only Murat's own words, never Claude's. Numbers come from `session_doc.json`, never
from estimation.

## Limits to be straight about

- The detector finds most errors, not all. In the 24.09 test, three real errors were only
  caught by the Step 4 reading pass.
- `errors per 100 words` is a trend signal across sessions, not an absolute grade. Compare
  voice with voice and typed with typed; a small typed sample swings a lot.
- The grammar range runs A1–C2 across 92 structures since 26.09.26: the original 50 plus 42
  B2–C2 points selected from the English Grammar Profile (Cambridge) in two batches (31 + 11)
  because a script can spot them. The sentence relative (", which was great" about a whole
  clause) was tried and left out: the parser can't tell it from an ordinary non-defining clause. Many EGP points depend on meaning (e.g. "would" for past habits looks like a
  conditional) and were deliberately left out. The five sessions before 26.09 were backfilled
  with the new points (each hit checked by hand). C2 structures (conditional inversion, hedging, subjunctive,
  advanced concession, three nested clauses) are rare in anyone's everyday speech, so weeks
  with none are normal. They show up more in careful typed writing.
- Word levels come from word lists, not meanings: "fine" counts as A1 whether it means
  "okay" or "a penalty". Everyday speech is about 84% A1 even for strong speakers, so watch
  the B2+ share and the actual advanced words, not the A1 figure.
- Off-list words get estimated levels (frequency guess, then Claude's judgement). They are
  marked "est." on the dashboard and are usually right or one step off (B2 vs C1). The five
  sessions before 26.09 were backfilled with each off-list word counted once, since their
  per-word counts weren't stored; from 26.09 on, real counts and voice/typed splits are used.
- Phrasal verb density is per clean word, the same count as the grammar side. Candidates are
  one per phrasal verb per sentence, so saying the same one twice in one sentence counts once.
  The script catches particles and tracker expressions reliably; new prepositional verbs not
  on the tracker depend on the `prep` rule and your extras, so a few may slip through.
- Vocab tracker (27.09.26): the list was imported from Murat's 23.09 file plus the 24–25.09 vocab
  session; the same day its 134 phrasal-verb items moved to the phrasal verb tracker (as "list"
  rows, 132 after merging duplicates like "bring up"), then 8 prepositional verbs (dwell on, cope
  with, appeal to...) followed, so the vocab tracker keeps 328 words and expressions (each with a
  `type`) and nothing is counted twice. Unprompted-use history only starts with the checked
  sessions (18.09 onwards), so most words start at Not Yet Observed; that's missing history, not
  proof he never used them. Idioms built on a phrasal verb (get the point across, go through the
  motions) stayed on the vocab list, and so did "come to" (regain consciousness), which would
  match too many ordinary phrases.
- Come-up matching works on word forms with small gaps allowed. It catches split phrasal
  verbs ("think it through") but needs the Step 4 check for loose matches.
- Unique words (added 29.09.26) count the different words Murat has *used* in checked chats, by
  base form, from 29.09.26 on. It is not his vocabulary size: he understands far more than he
  says, and everyday topics repeat. The first check sets a baseline (several hundred words), so
  judge the slope after that, not the first jump. Proper nouns, numbers and fillers are excluded;
  a misspoken word the transcriber turned into a real word will slip in now and then.
- Lexical diversity (MTLD, added 26.09.26) counts every word form as its own word ("go" and
  "went" differ) after fillers and repeats are stripped. Speech scores lower than writing for
  everyone (ideas get repeated out loud), so compare voice with voice. Under 100 words it's left
  blank; typed samples of a few hundred words still swing. There's no reliable native benchmark
  for transcribed conversation, so read it as his own trend. The five sessions before 26.09 were
  backfilled from the saved chats (voice word counts matched the ledger exactly in four of five).
- Turkish interference (added 27.09.26) is judged by two independent readers, not a script, so it
  is less mechanical than the grammar side. Every flag must name a Turkish source, which keeps it
  honest, but a flag says "this looks Turkish-shaped", not what Murat was thinking. In the pilot the
  two passes agreed on about 70–80% of flags; Murat confirmed the disputed types. The six sessions
  from 18 to 25 Sept were backfilled on 27.09 with the same method. Upgrades (correct but less
  natural) are listed separately and never counted.
- Impact labels (added 30.09.26) are Claude's judgement, like the fixes: consistent rules, not a
  measurement. The nine sessions from 18 to 29 Sept were labelled by hand on 30.09 (468 errors).
  Shares move with how many errors the check finds, so read the trend together with the method
  notes.
- Chunk counts (added 12.10.26) cover only the words and patterns in each chunk's definition; similar
  mistakes outside it are still errors but don't count for the chunk. Chunk 3 ("to", not "for +
  -ing") is rough: correct purpose clauses are hard to find mechanically. Rare chunks give few uses
  per session, which is why the settled rule pools the last 12 uses. Tested 12.10.26: 109/109 example
  sentences across all nine finders, 6/6 rolling-rule cases, and the 10.10 session (24 candidates,
  3 set by hand) matched a hand count. "As you just said" and similar phrases are left out of slice 2.
- Preposition accuracy (added 16.10.26) can read a little high: a slip this check misses counts as
  right. A watch-list row is one word, so other uses of the same word count too ("book" the noun under
  "book the tickets"). Plain "to" before a verb is never counted.
- Sentences with a slip (added 28.10.26) depend on how the speech-to-text punctuated the transcript:
  one long run-on sentence or three short ones changes the count. Read it as a trend. An error the
  script can't place counts as its own sentence, so the figure leans slightly high, never low.
  Tested 28.10.26 on a hand-counted sample (4 of 7 sentences, two errors in one sentence counted once).
- Pronunciation, fluency and pauses aren't measured. Only the transcript text is available.

## Scripts

In `scripts/` (copied to `/tmp/nc` in Step 1): `detect.py`, `vocab.py`, `session.py`, `vt_apply.py`, `pv.py`, `pv_apply.py`, `phave_link.py`, `lex_apply.py`, `intf.py`, `overview.py`, `chunks.py`, `preps.py`, `intf_instructions.md`. `sentences.py` (28.10.26) is written from Step 6 instead, since it lives in this file.