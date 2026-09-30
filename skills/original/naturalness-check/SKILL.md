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
native benchmark, tracker come-ups, new words). The tracker lives in the ledger database
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

Why it is built this way (rebuilt 25.09.26): the earlier version asked Claude to read the
transcript and "notice" patterns. On a real 100+ minute thread that found 5 items. The same
thread through this pipeline gave 186 verified observations and 24 real errors. The difference:
scripts parse every sentence and flag every match mechanically, and Claude's job is to
check each flag, not to find them. Do not replace any step below with "just read it and
judge". That is the approach that failed.

Dashboard: https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK ("Fluency Ledger").
Its database has `meta/registry` (grammar concept ids → [label, CEFR level]),
`meta/vocab_tracker` (Murat's vocabulary list: `{as_of, max_id, rows: [{id, expr, added,
importance, mastered, practice: {count, last}, dates[], notes}]}`; `dates` = days used unprompted),
`meta/pv_tracker` (the phrasal verb tracker: `{as_of, rows: [{word, dates[], notes, list?, practice?}]}`;
`list` marks a phrasal verb on Murat's study list),
`meta/interference` (the Turkish-interference pattern list: `{types, patterns: [{key, label, turkish,
type, fix}]}`) and one document per checked chat in `sessions`.

## Step 1: Set up the tools

The nine scripts and the interference pass instructions live at the bottom of this file. Extract them into a work folder, using the
skill's base directory (shown when the skill loads), and fetch the CEFR wordlists:

```bash
mkdir -p /tmp/nc && cd /tmp/nc
python3 - "<SKILL_BASE_DIR>/SKILL.md" << 'EOF'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
for name, body in re.findall(r"<!-- file: (\S+) -->\s*```(?:python|markdown)\n(.*?)```", text, re.S):
    open(name, "w", encoding="utf-8").write(body); print("wrote", name)
EOF
python3 -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null || \
  { pip install --break-system-packages -q spacy && python3 -m spacy download en_core_web_sm; }
[ -d /tmp/nc/olp ] || git clone -q --depth 1 https://github.com/openlanguageprofiles/olp-en-cefrj /tmp/nc/olp
python3 -c "import wordfreq" 2>/dev/null || pip install --break-system-packages -q wordfreq
```

`wordfreq` only supplies a starting guess for the level of off-list words (Step 4). If it
won't install, vocab.py still runs; the suggestions are just blank and you assign every
off-list level yourself.

Then fetch everything the check may change, in one go: `ArtifactData` `list` collection `meta`
with `out_dir: /tmp/nc` (it saves `meta/vocab_tracker`, `meta/pv_tracker`, `meta/interference`,
`meta/phave`, `meta/registry` and `meta/lexicon` under `/tmp/nc/meta/`). Note the `version` of each of those
six docs from the listing (`meta/lexicon` only exists after the first check from 29.09.26 on): Step 6 writes them back with `if_version`. (`meta/vocab_items` is the
old copy of the list from before 27.09.26; don't use it.)

**One save, one approval (28.09.26).** The app asks Murat to approve every write to the ledger,
and it offers him no "always allow". So this check reads whatever it needs up front and writes
**everything in a single `ArtifactData` `batch` call in Step 6**: never a separate `set`
earlier, never a follow-up write afterwards. Reads don't change anything; keep all writes for
Step 6.

If SKILL.md isn't readable from the sandbox, write the scripts from the code blocks below with
the file tool instead. If spaCy can't be installed (no network to PyPI/GitHub), stop and tell
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
  trigger message);
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
Uses of those words in this chat are practice, not spontaneous come-ups,
so vocab.py and pv.py skip them, and `vt_apply.py` (Step 5) records them as one review each.
Include words from both phases (artifact quiz and story loop). If the session ran over two
chats (quiz in one, stories in the next), list the words in each chat's check.

If the chat is very long and you have to stop paging early, say so in the report
("covers turns 0–N of M"). Never present a partial check as the whole session.

## Step 3: Run the detectors

```bash
cd /tmp/nc && python3 detect.py murat_turns.txt candidates.json
python3 vocab.py murat_turns.txt meta/vocab_tracker.json olp vocab_candidates.json drilled_words.txt
python3 pv.py murat_turns.txt meta/pv_tracker.json pv_candidates.json drilled_words.txt
```

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
and flags (`tracker` / `NEW`, `split`, `drilled`). Drilled words are left out of every count
automatically.

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

They must not see each other's output. Then merge:

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
  talking about a word, a transcription artefact, or no concrete Turkish source. Also drop moves
  inside a game (Murat's rule, 27.09.26): "that's true" / "correct" / "yes, that's it" used to
  confirm Claude's guesses in the Taboo game, and similar scoring or turn-taking phrases, are not
  slips, even when they match a pattern such as `true_correct`. The 18.09 session was recounted
  on 27.09 for this reason (106 -> 86 items). Drop any "let's say" item (Murat, 29.09.26: no longer
  counted; the pattern `lets_say_filler` now means "how to say" / "how can I say" only). All eight
  sessions to 28.09 were recounted on 29.09 without "let's say" (82 items removed).
- **pattern**: if a pass used an unknown key or a `new:` label, map it to an existing key when one
  fits. Add a **new pattern** only for something that recurs (2+ times) or is clearly distinct;
  otherwise use the matching `other_*` key. A new pattern needs `{key, label, turkish, type, fix}`,
  with a label Murat will understand on the dashboard.
- **upgrade_drop**: upgrade suggestions that are only taste, not a clearly more natural choice.
Write `/tmp/nc/intf_verdicts.json`: `{"drop": [..], "pattern": {"index": "key"}, "upgrade_drop": [..],
"new_patterns": [..]}` (empty lists/objects are fine).

Write `/tmp/nc/verdicts.json`:

```json
{"drop": [12, 40],
 "error": {"57": "it's been started -> it started"},
 "fix": {"3": "despite + clause -> even though ...", "8": "'in the meantime' used for 'by the way' -> anyway"},
 "relabel": {"8": "err_in_the_meantime"},
 "extra": [{"concept": "err_preposition", "turn": "T56",
            "mode": "voice", "sentence": "will take me to another five weeks",
            "fix": "will take me another five weeks"}],
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
```

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
items, comeups, new_words). If it prints `STOP: … error(s) have no fix`, it has written
nothing: add the listed fixes to verdicts.json and rerun it before the other scripts.
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
To know whether the session doc already exists, `list` the `sessions` collection (reading
only; you need that listing for the Step 7 comparison anyway) and note its `version` if it does.

## Step 6: Write it to the dashboard, in one save

Make **one** `ArtifactData` `batch` call (`url` = the dashboard link) holding every write, so
Murat approves once. Include an entry only when its file exists:

| op | collection | doc_id | file_path | if_version |
|---|---|---|---|---|
| set | sessions | `<doc_id>` | /tmp/nc/session_doc.json | its version if the doc already existed, else leave out |
| set | meta | pv_tracker | /tmp/nc/pv_tracker_out.json | from Step 1 |
| set | meta | vocab_tracker | /tmp/nc/vocab_tracker_out.json | from Step 1 |
| set | meta | interference | /tmp/nc/meta_interference_out.json (only if it exists) | from Step 1 |
| set | meta | phave | /tmp/nc/phave_out.json (only if it exists) | from Step 1 |
| set | meta | registry | /tmp/nc/registry_out.json (only if it exists) | from Step 1 |
| set | meta | lexicon | /tmp/nc/lexicon_out.json | from Step 1; leave out if the doc didn't exist yet |

For example:

```json
[{"op": "set", "collection": "sessions", "doc_id": "s_20260929_1a2b3c4d", "file_path": "/tmp/nc/session_doc.json"},
 {"op": "set", "collection": "meta", "doc_id": "pv_tracker", "file_path": "/tmp/nc/pv_tracker_out.json", "if_version": 9},
 {"op": "set", "collection": "meta", "doc_id": "vocab_tracker", "file_path": "/tmp/nc/vocab_tracker_out.json", "if_version": 5}]
```

The batch is all or nothing. If it fails because a doc changed meanwhile (Murat may have added a
word, or a vocab session recorded reviews), nothing was written: fetch that doc again, rerun the
script that builds it (`pv_apply.py` then `vt_apply.py` for the trackers, `phave_link.py` for
`meta/phave`, `lex_apply.py` for `meta/lexicon`), and send the whole batch again. Never split it into separate writes to get
round a conflict.

Never write the tracker .docx or a vocab .docx into the Project; the ledger is the only home.

## Step 7: Report

**Text chat:**
1. One line: words analyzed, observations, errors, and errors per 100 words **for voice and
   typed separately** (from `by_mode`), each with its change from the previous session.
   `list` the `sessions` collection, take the doc before this one, and compare. If one mode
   has under ~500 words, say its rate is based on a small sample.
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
7. The dashboard link for the full view (the Phrasal verbs tab shows the whole tracker, the
   Naturalness tab the interference patterns, the Vocabulary tab the vocab tracker).

**Voice mode:** keep it short and spoken. Give the error rate, the top two error types with
one example each, one good structure, the phrasal verb density, the interference rate with the
top pattern, and one vocab-list come-up if there was one. Say the
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
- Pronunciation, fluency and pauses aren't measured. Only the transcript text is available.

## Scripts

<!-- file: detect.py -->
```python
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
```

<!-- file: vocab.py -->
```python
#!/usr/bin/env python3
"""
Vocabulary side of the naturalness check.

1. CEFR profile: every word Murat used is looked up in the CEFR-J list (A1-B2)
   and the Octanove list (C1-C2) -> level distribution + the B2+ words he used.
2. Vocab-file come-ups: every expression on his vocabulary list is matched
   against his sentences (lemmas, gaps allowed for objects/separable particles),
   so a practised word that turns up unprompted is logged with its quote.
3. Lexical diversity (MTLD): how varied his words are, voice and typed separately.

Like detect.py, this only FINDS candidates. Claude reviews the REVIEW LIST and
drops false hits (quoting a text, talking about a word, words drilled in that
chat's vocab session) before anything is logged.

Usage: python3 vocab.py murat_turns.txt vocab_items.json <cefr_dir> vocab_candidates.json [drilled_words.txt]
  vocab_items.json: meta/vocab_tracker ({"rows": [{"id": 49, "expr": "Dwell (on something)", ...}]});
  the old {"items": [...]} shape is also accepted
  cefr_dir: clone of github.com/openlanguageprofiles/olp-en-cefrj
"""
import csv, json, os, re, sys
from collections import Counter
import spacy
from detect import clean, load_turns
try:
    from wordfreq import zipf_frequency
except ImportError:
    zipf_frequency = None

def suggest_level(z):
    """Rough frequency -> CEFR guess for words missing from both lists. Claude reviews every one."""
    if z is None: return None
    return "A1" if z >= 5 else "A2" if z >= 4.5 else "B1" if z >= 4 else "B2" if z >= 3.5 else "C1" if z >= 3 else "C2"

nlp = spacy.load("en_core_web_sm")
RANK = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

def mtld(tokens, ttr=0.72, min_len=10):
    """MTLD (McCarthy & Jarvis 2010), TAALED variant: a factor closes when the running
    type-token ratio drops below 0.72 with at least 10 words; the leftover counts as a
    partial factor; forwards and backwards are averaged. Higher = more varied words.
    Matches the lexical_diversity package's mtld() exactly (checked 26.09.26)."""
    def one_way(ts):
        factors, types, count = 0.0, set(), 0
        for t in ts:
            count += 1; types.add(t)
            if len(types) / count < ttr and count >= min_len:
                factors += 1; types, count = set(), 0
        if count:
            factors += (1 - len(types) / count) / (1 - ttr)
        return len(ts) / factors if factors else 0.0
    return (one_way(tokens) + one_way(tokens[::-1])) / 2

MTLD_MIN = 100   # below this many words MTLD isn't meaningful; stored as null

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
    """Lemma first, then surface form, then fold common derivations back to a base."""
    w, l = tok.text.lower(), tok.lemma_.lower()
    for c in (l, w):
        if c in lvl: return lvl[c], c
    cands = []
    if w.endswith("ily"): cands.append(w[:-3] + "y")
    if w.endswith("ly"): cands += [w[:-2], w[:-2] + "e"]
    if w.endswith("ing"): cands += [w[:-3], w[:-3] + "e"]
    if w.endswith("ed"): cands += [w[:-2], w[:-1], w[:-2] + "e"]
    if w.endswith("ness"): cands.append(w[:-4])
    for c in cands:
        if c in lvl: return lvl[c], c
    return None, l

WILD = {"something", "someone", "somebody", "someone's", "somewhere", "your", "yourself",
        "you", "x", "y", "their", "his", "her", "my", "you've", "do", "doing"}
# A pattern that shrinks to one of these single words would fire on almost any
# sentence ("make it" -> "make", "be through" -> "through"), so it is skipped.
TOO_COMMON = {"make", "get", "go", "come", "keep", "take", "have", "put", "do", "give", "look",
              "run", "set", "turn", "bring", "through", "up", "down", "out", "off", "in", "on"}

PREP = {"to", "with", "for", "at", "by", "of", "into", "about", "from"}

def expand_alts(expr):
    """'Go/come full circle' -> ['go full circle', 'come full circle'];
    'Slope up/down' -> ['slope up', 'slope down']; 'A / B' -> ['A', 'B']."""
    out = []
    for part in re.split(r"\s+/\s+", expr):
        m = re.search(r"(\S+)/(\S+)", part)
        if m:
            out += [part[:m.start()] + m.group(1) + part[m.end():], part[:m.start()] + m.group(2) + part[m.end():]]
        else:
            out.append(part)
    return out
LEAD = {"to", "be", "being", "a", "an", "the"}

def compile_items(items):
    pats = []
    for it in items:
        for alt in expand_alts(it["expr"]):
            s = re.sub(r"\([^)]*\)", " ", alt.lower())
            s = re.sub(r"\+\s*-ing", " ", s).replace("-", " ")
            toks = s.split()
            while toks and toks[0] in LEAD and len(toks) > 1: toks = toks[1:]
            if not toks: continue
            seq = []  # list of (lemma, gap_allowed_before)
            gap = 0
            doc = nlp(" ".join(toks))
            for t in doc:
                if t.text in WILD or t.text == "'s":
                    gap = 3; continue
                if not t.is_alpha and t.text != "'t": continue
                seq.append((t.lemma_.lower(), gap if seq else 0))
                gap = 2
            if not seq or (len(seq) == 1 and seq[0][0] in TOO_COMMON): continue
            if len(seq) == 2 and seq[0][0] in TOO_COMMON and seq[1][0] in PREP: continue   # "get to", "come to"
            pats.append({"id": it["id"], "expr": it["expr"], "seq": seq})
    return pats

def match(seq, lemmas):
    """Ordered lemma match; each token may sit up to `gap` tokens after the previous."""
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

def mtld_block(div):
    allw = div["voice"] + div["typed"]
    val = lambda ws: round(mtld(ws), 1) if len(ws) >= MTLD_MIN else None
    return {"all": val(allw), "voice": val(div["voice"]), "typed": val(div["typed"]),
            "words": {m: len(ws) for m, ws in div.items()}}

def main(turns_path, items_path, cefr_dir, out, drilled_path=None):
    """drilled_path: optional file, one expression per line, of words drilled in this
    chat's vocab session. Their hits are counted as practice, not spontaneous come-ups."""
    lvl = load_levels(cefr_dir)
    drilled = set()
    if drilled_path and os.path.exists(drilled_path):
        drilled = {l.strip().lower() for l in open(drilled_path, encoding="utf-8") if l.strip()}
    src = json.load(open(items_path)); src = src.get("data", src)
    items = [{"id": it["id"], "expr": it["expr"]} for it in (src.get("items") or src["rows"])
             if it["expr"].strip().lower() not in drilled]
    pats = compile_items(items)
    levels, tokens = Counter(), 0
    mlevels = {"voice": Counter(), "typed": Counter()}
    adv, off, hits = {}, Counter(), []
    off_mode, off_sent = {}, {}
    seen_hit = set()
    div = {"voice": [], "typed": []}   # word tokens for MTLD, same word rule as detect.py
    uniq = set()
    for turn, raw, mode in load_turns(turns_path):
        div[mode] += [w.lower() for w in re.findall(r"[A-Za-z']+", clean(raw))]
        doc = nlp(clean(raw))
        for s in doc.sents:
            lemmas = [t.lemma_.lower() for t in s]
            for p in pats:
                key = (p["id"], turn)
                if key in seen_hit: continue
                if match(p["seq"], lemmas):
                    seen_hit.add(key)
                    hits.append({"id": p["id"], "expr": p["expr"], "turn": turn, "mode": mode, "sentence": s.text.strip()})
            for t in s:
                if not t.is_alpha or t.pos_ == "PROPN": continue
                uniq.add(t.lemma_.lower())   # unique words: lemmas, so go/went/gone count once
                L, base = level_of(t, lvl)
                if L:
                    levels[L] += 1; tokens += 1; mlevels[mode][L] += 1
                    if RANK[L] >= 4 and base not in adv:
                        adv[base] = {"word": base, "level": L, "turn": turn, "mode": mode, "sentence": s.text.strip()}
                elif len(t.text) >= 5:
                    w = t.lemma_.lower()
                    # spaCy sometimes invents a lemma ("knackered" -> "knackere"); keep the real word
                    if zipf_frequency and zipf_frequency(w, "en") == 0 and zipf_frequency(t.text.lower(), "en") > 0:
                        w = t.text.lower()
                    off[w] += 1
                    off_mode.setdefault(w, Counter())[mode] += 1
                    off_sent.setdefault(w, s.text.strip())
    cands = []
    for h in hits: cands.append({"i": len(cands), "type": "comeup", **h})
    for a in sorted(adv.values(), key=lambda a: (-RANK[a["level"]], a["word"])):
        cands.append({"i": len(cands), "type": "advanced", **a})
    offlist = []
    for w, c in off.most_common(60):
        z = round(zipf_frequency(w, "en"), 2) if zipf_frequency else None
        offlist.append({"word": w, "count": c, "by_mode": dict(off_mode[w]), "zipf": z,
                        "suggested": suggest_level(z), "sentence": off_sent[w][:300]})
    result = {"tokens": tokens,
              "level_counts": {k: levels[k] for k in RANK},
              "level_counts_by_mode": {m: {k: c[k] for k in RANK} for m, c in mlevels.items()},
              "levels": {k: round(levels[k] / tokens * 100, 1) if tokens else 0 for k in RANK},
              "levels_by_mode": {m: {"tokens": sum(c.values()),
                                     "levels": {k: round(c[k] / sum(c.values()) * 100, 1) if c else 0 for k in RANK}}
                                 for m, c in mlevels.items()},
              "offlist": offlist,
              "mtld": mtld_block(div),
              "lemmas": sorted(uniq),
              "candidates": cands}
    json.dump(result, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"{tokens} words on the CEFR lists · levels: " + " ".join(f"{k} {v}%" for k, v in result["levels"].items()))
    md = result["mtld"]
    print(f'lexical diversity (MTLD): voice {md["voice"]} ({md["words"]["voice"]} words) · typed {md["typed"]} ({md["words"]["typed"]} words) · all {md["all"]}')
    print("VOCAB REVIEW LIST  (index | type | item or word | sentence)")
    for c in cands:
        label = f'#{c["id"]} {c["expr"]}' if c["type"] == "comeup" else f'{c["word"]} ({c["level"]})'
        print(f'{c["i"]:4} | {c["type"]:8} | {label} | {c["turn"]} {c["mode"][0]}: {c["sentence"][:160]}')
    print("OFF-LIST REVIEW  (word | count | zipf -> suggested level | sentence)")
    for o in offlist:
        print(f'  {o["word"]} | {o["count"]} | {o["zipf"]} -> {o["suggested"] or "?"} | {o["sentence"][:140]}')

if __name__ == "__main__":
    main(*sys.argv[1:6])
```

<!-- file: session.py -->
```python
#!/usr/bin/env python3
"""
Merge detector candidates with Claude's verdicts into one session document
for the Fluency Ledger dashboard (collection "sessions").

verdicts.json (written by Claude after reviewing the REVIEW LIST):
{
  "drop":    [12, 40],                      # false positives, discarded
  "error":   {"57": "it's been started -> it started"},   # use-candidates that were actually wrong (+ fix)
  "fix":     {"3": "despite + clause -> even though ..."},  # optional fix text for detector-flagged errors
  "relabel": {"8": "err_in_the_meantime"},  # move a candidate to another concept id
  "extra":   [ {"concept": "err_preposition", "turn": "T56", "mode": "voice",
                "sentence": "...", "result": "error", "fix": "..."} ]   # errors the detector missed
}
Defaults: detector "use" -> correct, detector "error" -> error.
Every error must end up with a fix (28.09.26): if any has none, the script prints them and
stops without writing the session. Add the missing fixes to verdicts.json and rerun.

Usage: python3 session.py candidates.json verdicts.json <DD.MM.YYYY> "<thread title>" <doc_id> session_doc.json [vocab_candidates.json]
"""
import sys, json
from collections import defaultdict

LEVEL_RANK = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
# fixes that are the same every time; a fix written in verdicts.json always wins
DEFAULT_FIX = {"err_in_the_meantime": "'in the meantime' used for 'by the way' -> by the way"}

RANKS = ["A1", "A2", "B1", "B2", "C1", "C2"]

def build_vocab(vc, v):
    """vc = vocab_candidates.json; v = verdicts ('vocab_drop': indices, 'offlist_drop': words,
    'offlist_levels': {word: level} = Claude's reviewed level for each kept off-list word)."""
    drop = set(int(x) for x in v.get("vocab_drop", []))
    offdrop = {w.lower() for w in v.get("offlist_drop", [])}
    offlv = {w.lower(): L for w, L in v.get("offlist_levels", {}).items() if L in RANKS}
    comeups, advanced = {}, []
    for c in vc["candidates"]:
        if c["i"] in drop: continue
        if c["type"] == "comeup":
            e = comeups.setdefault(c["id"], {"id": c["id"], "expr": c["expr"], "count": 0, "quote": c["sentence"][:300]})
            e["count"] += 1
        else:
            advanced.append({"word": c["word"], "level": c["level"], "quote": c["sentence"][:300]})
    # list-graded counts
    base = vc.get("level_counts") or {k: round(vc["tokens"] * vc["levels"].get(k, 0) / 100) for k in RANKS}
    base_m = vc.get("level_counts_by_mode", {})
    tot = {k: base.get(k, 0) for k in RANKS}
    tot_m = {m: {k: c.get(k, 0) for k in RANKS} for m, c in base_m.items()}
    # add off-list words with their estimated level
    kept, est_tokens, have = [], 0, {a["word"] for a in advanced}
    for o in vc["offlist"]:
        w = o["word"]
        if w in offdrop: continue
        L = offlv.get(w) or o.get("suggested")
        kept.append({"word": w, "level": L, "est": True, "count": o["count"]})
        if not L: continue
        tot[L] += o["count"]; est_tokens += o["count"]
        for m, n in o.get("by_mode", {}).items():
            tot_m.setdefault(m, {k: 0 for k in RANKS})[L] += n
        if RANKS.index(L) >= 3 and w not in have:
            advanced.append({"word": w, "level": L, "quote": o.get("sentence", "")[:300], "est": True})
    pct = lambda c: {k: round(c[k] / sum(c.values()) * 100, 1) if sum(c.values()) else 0 for k in RANKS}
    b2 = lambda l: round(l.get("B2", 0) + l.get("C1", 0) + l.get("C2", 0), 1)
    lv = pct(tot)
    return {
        "b2plus_by_mode": {m: (b2(pct(c)) if sum(c.values()) else None) for m, c in tot_m.items()},
        "tokens": sum(tot.values()),
        "tokens_list": vc["tokens"],
        "levels": lv,
        "b2plus_share": b2(lv),
        "b2plus_share_list": b2(vc["levels"]),
        "est": {"words": sum(1 for k in kept if k["level"]), "tokens": est_tokens,
                "basis": "frequency suggestion reviewed by Claude"},
        "advanced": advanced,
        "offlist": kept[:25],
        "comeups": sorted(comeups.values(), key=lambda e: -e["count"]),
        "mtld": vc.get("mtld"),
    }

def build_pv(pc, v, tracker_words):
    """pc = pv_candidates.json; v = verdicts ('pv_drop': indices, 'pv_relabel': {index: tracker word},
    'pv_extra': [{word, turn, mode, sentence}], 'pv_notes': {word: note})."""
    drop = set(int(x) for x in v.get("pv_drop", []))
    rel = {int(k): w for k, w in v.get("pv_relabel", {}).items()}
    uses = []
    for c in pc["candidates"]:
        if c["i"] in drop or c.get("drilled"): continue   # drilled vocab words are practice, not evidence
        uses.append({"word": rel.get(c["i"], c["word"]), "mode": c["mode"], "sentence": c["sentence"]})
    for x in v.get("pv_extra", []):
        uses.append({"word": x["word"], "mode": x.get("mode", "voice"), "sentence": x.get("sentence", "")})
    items = {}
    for u in uses:
        it = items.setdefault(u["word"], {"word": u["word"], "count": 0, "modes": [], "quote": u["sentence"][:300]})
        it["count"] += 1
        if u["mode"] not in it["modes"]: it["modes"].append(u["mode"])
    words = pc["words"]; W = sum(words.values())
    by_mode = {m: {"words": words.get(m, 0), "instances": sum(1 for u in uses if u["mode"] == m)} for m in ("voice", "typed")}
    tw = set(tracker_words)
    return {
        "words": W, "instances": len(uses), "distinct": len(items),
        "per_1000": round(len(uses) / W * 1000, 2) if W else None,
        "by_mode": by_mode,
        "items": sorted(items.values(), key=lambda i: (-i["count"], i["word"])),
        "comeups": sorted(w for w in items if w in tw),
        "new_words": sorted(w for w in items if w not in tw),
        "notes": {w: n for w, n in v.get("pv_notes", {}).items() if n},
    }

def main(cpath, vpath, date, title, doc_id, out, vocab_path=None, pv_path=None, tracker_path=None):
    data = json.load(open(cpath)); v = json.load(open(vpath))
    drop = set(int(x) for x in v.get("drop", []))
    err = {int(k): t for k, t in v.get("error", {}).items()}
    fix = {int(k): t for k, t in v.get("fix", {}).items()}
    rel = {int(k): t for k, t in v.get("relabel", {}).items()}

    items = []
    for c in data["candidates"]:
        i = c["i"]
        if i in drop: continue
        concept = rel.get(i, c["concept"])
        if i in err or c["kind"] == "error" or concept.startswith("err_"):
            items.append({"concept": concept, "level": c["level"] if not concept.startswith("err_") else None,
                          "result": "error", "quote": c["sentence"],
                          "fix": (err.get(i) or fix.get(i) or DEFAULT_FIX.get(concept, "")).strip(),
                          "mode": c.get("mode", "typed"), "src": f"index {i}"})
        else:
            items.append({"concept": concept, "level": c["level"], "result": "correct", "quote": c["sentence"],
                          "mode": c.get("mode", "typed")})
    for n, x in enumerate(v.get("extra", [])):
        items.append({"concept": x["concept"], "level": x.get("level"), "result": x.get("result", "error"),
                      "quote": x["sentence"], "fix": (x.get("fix") or DEFAULT_FIX.get(x["concept"], "")).strip(),
                      "mode": x.get("mode", "typed"), "src": f"extra #{n}"})

    missing = [it for it in items if it["result"] == "error" and not it["fix"]]
    if missing:
        print(f"STOP: {len(missing)} error(s) have no fix. Add each to verdicts.json "
              "(\"fix\": {index: ...} for detector lines, \"fix\" inside the item for extras) and rerun:")
        for it in missing:
            print(f'  {it["src"]} | {it["concept"]} | {it["quote"][:150]}')
        sys.exit(1)

    counts = defaultdict(lambda: {"correct": 0, "error": 0, "level": None})
    for it in items:
        c = counts[it["concept"]]; c[it["result"]] += 1; c["level"] = c["level"] or it["level"]

    errors = [{"concept": it["concept"], "quote": it["quote"][:300], "fix": it.get("fix", ""), "mode": it["mode"]}
              for it in items if it["result"] == "error"]
    wbm = data.get("words_by_mode", {"voice": 0, "typed": data["words"]})
    by_mode = {}
    for m in ("voice", "typed"):
        e = sum(1 for x in errors if x["mode"] == m)
        by_mode[m] = {"words": wbm.get(m, 0), "errors": e,
                      "errors_per_100": round(e / wbm[m] * 100, 2) if wbm.get(m) else None}
    # highlights: correct uses at B2+ (one quote per concept, first seen)
    seen, highlights = set(), []
    for it in items:
        if it["result"] == "correct" and LEVEL_RANK.get(it["level"] or "", 0) >= 4 and it["concept"] not in seen:
            seen.add(it["concept"]); highlights.append({"concept": it["concept"], "quote": it["quote"][:300]})

    correct_concepts = [k for k, c in counts.items() if c["correct"] > 0 and not k.startswith("err_")]
    top = max((LEVEL_RANK.get(counts[k]["level"] or "", 0) for k in correct_concepts), default=0)
    words = data["words"]
    doc = {
        "date": date, "title": title,
        "words": words,
        "observations": len(items),
        "errors_total": len(errors),
        "errors_per_100": round(len(errors) / words * 100, 2) if words else None,
        "range_concepts": len(correct_concepts),
        "b2plus_correct": sum(c["correct"] for k, c in counts.items() if LEVEL_RANK.get(c["level"] or "", 0) >= 4),
        "top_level": {v: k for k, v in LEVEL_RANK.items()}.get(top),
        "concepts": {k: {"correct": c["correct"], "error": c["error"]} for k, c in sorted(counts.items())},
        "by_mode": by_mode,
        "errors": errors,
        "highlights": highlights,
    }
    if vocab_path:
        doc["vocab"] = build_vocab(json.load(open(vocab_path)), v)
    if pv_path and tracker_path:
        doc["pv"] = build_pv(json.load(open(pv_path)), v, [r["word"] for r in json.load(open(tracker_path)).get("rows", [])])
    json.dump(doc, open(out, "w"), indent=1, ensure_ascii=False)
    if vocab_path:
        vv = doc["vocab"]
        print(f'vocab: B2+ share {vv["b2plus_share"]}% · {len(vv["advanced"])} B2+ words · {len(vv["comeups"])} vocab-file come-ups')
        if vv.get("mtld"):
            print(f'lexical diversity (MTLD): voice {vv["mtld"]["voice"]} · typed {vv["mtld"]["typed"]}')
    print(json.dumps({k: doc[k] for k in ("date", "words", "observations", "errors_total", "errors_per_100",
                                           "range_concepts", "b2plus_correct", "top_level", "by_mode")}, indent=1))
    if doc.get("pv"):
        p = doc["pv"]
        dens = f'1 per {round(p["words"] / p["instances"])} words' if p["instances"] else "no phrasal verbs"
        print(f'phrasal verbs: {p["instances"]} uses, {p["distinct"]} different, {dens} (native 1 per 192) · '
              f'{len(p["comeups"])} tracker come-ups · new: {", ".join(p["new_words"]) or "none"}')
    print("doc_id:", doc_id)

if __name__ == "__main__":
    main(*sys.argv[1:10])
```

<!-- file: vt_apply.py -->
```python
#!/usr/bin/env python3
"""
Update the vocabulary tracker (meta/vocab_tracker) from one checked session.

- Every verified vocab-file come-up in session_doc.json (vocab.comeups) adds the
  session date to that row's `dates` (days used unprompted). One date per row per day.
- Every word in drilled_words.txt (this chat's vocab session) counts as one review:
  practice.count +1 and practice.last = date, once per day. Drilled uses never go
  into `dates`: story and quiz uses are practice, not unprompted use.
- Drilled phrasal verbs (study-list items living in meta/pv_tracker since 27.09.26) are
  recorded the same way on their pv row's `practice`, in the pv tracker file given as the
  last argument (the pv_apply.py output), which is rewritten in place.
- Rows are never added here. Only Murat adds words to his list.

Stages use the phrasal verb tracker's rules on the number of different days used:
0 Not Yet Observed, 1-2 Emerging, 3-5 In Progress, 6+ Activated.
`mastered` is Murat's own label and is never changed here.

Usage: python3 vt_apply.py vocab_tracker.json session_doc.json DD.MM.YYYY out.json [drilled_words.txt] [pv_tracker_out.json]
"""
import json, os, sys

def stage(n):
    return "Not Yet Observed" if n == 0 else "Emerging" if n <= 2 else "In Progress" if n <= 5 else "Activated"

def dkey(d):
    a, b, c = d.split("."); return c + b + a

def main(tr_path, sess_path, date, out, drilled_path=None, pv_path=None):
    tr = json.load(open(tr_path)); tr = tr.get("data", tr)
    s = json.load(open(sess_path)); s = s.get("data", s)
    rows = tr["rows"]; by_id = {r["id"]: r for r in rows}
    by_expr = {r["expr"].strip().lower(): r for r in rows}
    pv = None
    if pv_path and os.path.exists(pv_path):
        pv = json.load(open(pv_path)); pv = pv.get("data", pv)
    by_pv = {r["word"].strip().lower(): r for r in (pv or {}).get("rows", [])}
    changes, stageups, missing = [], [], []
    for cu in (s.get("vocab") or {}).get("comeups", []):
        r = by_id.get(cu["id"])
        if not r: missing.append(f'come-up id {cu["id"]} {cu.get("expr")}'); continue
        before = stage(len(r["dates"]))
        if date not in r["dates"]:
            r["dates"].append(date); r["dates"].sort(key=dkey)
            changes.append(f'used: #{r["id"]} {r["expr"]}')
            after = stage(len(r["dates"]))
            if after != before: stageups.append(f'#{r["id"]} {r["expr"]} -> {after}' + (" (Mastered)" if r.get("mastered") else ""))
    if drilled_path and os.path.exists(drilled_path):
        for w in (l.strip() for l in open(drilled_path, encoding="utf-8")):
            if not w: continue
            r = by_expr.get(w.lower())
            label = f'#{r["id"]} {r["expr"]}' if r else None
            if not r and w.lower() in by_pv:
                r = by_pv[w.lower()]; label = f'phrasal verb: {r["word"]}'
            if not r: missing.append(f'drilled word not on either list: {w}'); continue
            p = r.setdefault("practice", {"count": 0, "last": None})
            if p.get("last") != date:
                p["count"] = p.get("count", 0) + 1; p["last"] = date
                changes.append(f'practised: {label}')
    tr["as_of"] = date
    json.dump(tr, open(out, "w"), ensure_ascii=False, indent=1)
    if pv is not None:
        json.dump(pv, open(pv_path, "w"), ensure_ascii=False)
    print(f"{len(changes)} changes")
    for c in changes: print(" ", c)
    print("STAGE-UPS:", "; ".join(stageups) or "none")
    if missing: print("CHECK:", "; ".join(missing))
    n = {}
    for r in rows:
        k = "Mastered" if r.get("mastered") else stage(len(r["dates"]))
        n[k] = n.get(k, 0) + 1
    print("counts:", n)

if __name__ == "__main__":
    main(*sys.argv[1:])
```

<!-- file: pv.py -->
```python
#!/usr/bin/env python3
"""
Phrasal verb side of the naturalness check (added 26.09.26; replaces the old
phrasal-verb-tracker skill's "read the chat and spot them" step, the same
eyeballing method that failed for grammar).

Finds every phrasal verb CANDIDATE in Murat's turns, three ways:
  A. spaCy particles: any verb with a `prt` child ("turn it off", "pick her up",
     "figure out") -> verb + particle, split forms included.
  B. Tracker matching: every expression on the tracker ("deal with",
     "take care of", "get back to (someone)") matched on lemmas with small gaps,
     so prepositional verbs that spaCy doesn't mark as particles are caught.
  C. Adverbial particles spaCy reads as prepositions right after a verb
     ("went through", "came across"), for words not yet on the tracker.
Claude then verifies every line (drop / relabel / extra) before anything counts.

Usage: python3 pv.py murat_turns.txt meta/pv_tracker.json pv_candidates.json [drilled_words.txt]
"""
import json, os, re, sys
import spacy
from detect import clean, load_turns
from vocab import expand_alts, match

nlp = spacy.load("en_core_web_sm")
PARTICLES_C = {"up", "down", "out", "off", "away", "back", "over", "around", "round", "through",
               "across", "along", "apart", "aside", "forward", "about", "into", "onto"}
SKIP_VERBS = {"be", "have", "do"}
WILD = {"something", "someone", "somebody", "someone's", "yourself", "it", "the", "a", "same",
        "page", "steam", "nowhere", "left"}

def canon(verb, prt):
    return f"{verb} {prt}".lower()

def compile_tracker(rows):
    """-> [{word, seq}] with seq = list of (lemma, gap) for vocab.match()."""
    pats = []
    for r in rows:
        for alt in expand_alts(r["word"]):
            s = re.sub(r"\([^)]*\)", " ", alt.lower()).replace("-", " ")
            toks = [t for t in nlp(" ".join(s.split()))]
            seq, gap = [], 0
            for t in toks:
                if t.text in WILD: gap = 3; continue
                if not t.is_alpha: continue
                seq.append((t.lemma_.lower(), gap if seq else 0)); gap = 2
            if len(seq) >= 2:
                pats.append({"word": r["word"], "seq": seq})
    return pats

def main(turns_path, tracker_path, out, drilled_path=None):
    rows = json.load(open(tracker_path)).get("rows", [])
    pats = compile_tracker(rows)
    # (verb, particle) -> tracker word, for mapping A/C hits onto tracker entries
    two = {}
    for p in pats:
        if len(p["seq"]) == 2: two.setdefault((p["seq"][0][0], p["seq"][1][0]), p["word"])
    drilled = set()
    if drilled_path and os.path.exists(drilled_path):
        drilled = {l.strip().lower() for l in open(drilled_path, encoding="utf-8") if l.strip()}
    words = {"voice": 0, "typed": 0}
    cands = []
    for turn, raw, mode in load_turns(turns_path):
        text = clean(raw)
        words[mode] += len(re.findall(r"[A-Za-z']+", text))
        for s in nlp(text).sents:
            lemmas = [t.lemma_.lower() for t in s]
            found = {}   # word -> {source, split, on_tracker, seq}
            for p in pats:
                if match(p["seq"], lemmas):
                    found.setdefault(p["word"], {"source": "tracker", "split": False, "on_tracker": True,
                                                 "seq": [l for l, _ in p["seq"]]})
            for v in s:
                if v.pos_ not in ("VERB", "AUX") or v.lemma_.lower() in SKIP_VERBS: continue
                for c in v.children:
                    src = None
                    if c.dep_ == "prt": src = "particle"
                    elif c.dep_ == "prep" and c.lower_ in PARTICLES_C and c.i == v.i + 1: src = "prep"
                    if not src: continue
                    key = (v.lemma_.lower(), c.lower_)
                    word = two.get(key, canon(*key))
                    f = found.setdefault(word, {"source": src, "split": False, "on_tracker": word in two.values(),
                                                "seq": list(key)})
                    f["split"] = f["split"] or c.i > v.i + 1
            # drop a match whose lemmas are the start of a longer match in the same sentence
            # ("got back" inside "get back to (someone)", "get back" inside it too)
            keep = {w: f for w, f in found.items()
                    if not any(o is not f and len(o["seq"]) > len(f["seq"]) and o["seq"][:len(f["seq"])] == f["seq"]
                               for o in found.values())}
            for word, f in keep.items():
                cands.append({"i": len(cands), "turn": turn, "mode": mode, "word": word, "source": f["source"],
                              "split": f["split"], "on_tracker": f["on_tracker"],
                              "drilled": word.lower() in drilled, "sentence": s.text.strip()})
    json.dump({"words": words, "candidates": cands}, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"{sum(words.values())} words (voice {words['voice']}, typed {words['typed']}) · {len(cands)} phrasal verb candidates")
    print("PHRASAL VERB REVIEW LIST  (index | word | source | flags | sentence)")
    for c in cands:
        flags = ",".join(f for f, on in (("tracker", c["on_tracker"]), ("NEW", not c["on_tracker"]),
                                         ("split", c["split"]), ("drilled", c["drilled"])) if on)
        print(f'{c["i"]:4} | {c["word"]} | {c["source"]} | {flags} | {c["turn"]} {c["mode"][0]}: {c["sentence"][:150]}')

if __name__ == "__main__":
    main(*sys.argv[1:5])
```

<!-- file: pv_apply.py -->
```python
#!/usr/bin/env python3
"""
Apply one checked session to the phrasal verb tracker stored in the ledger
(meta/pv_tracker). Adds the session date to every tracker word that came up,
adds first-time words with that date, and appends any notes. One date per word
per day, so re-running the check in the same chat changes nothing twice.

Stage, recency and signal are NOT stored: the ledger page and the .docx export
work them out from the dates, so they are always current.

Usage: python3 pv_apply.py meta/pv_tracker.json session_doc.json <DD.MM.YYYY> pv_tracker_out.json
"""
import json, sys
from datetime import datetime

def d(s): return datetime.strptime(s, "%d.%m.%Y")

def main(tpath, spath, date, out):
    doc = json.load(open(tpath)); p = json.load(open(spath)).get("pv")
    if not p: print("session has no phrasal verb data; tracker unchanged"); json.dump(doc, open(out, "w"), ensure_ascii=False); return
    rows = doc["rows"]; by = {r["word"]: r for r in rows}
    before = {r["word"]: len(set(r["dates"])) for r in rows}
    changes = []
    for w in p["comeups"]:
        r = by[w]
        if date not in r["dates"]: r["dates"].append(date); changes.append(f"come-up: {w}")
    for w in p["new_words"]:
        if w in by:
            if date not in by[w]["dates"]: by[w]["dates"].append(date); changes.append(f"come-up: {w}")
            continue
        r = {"word": w, "dates": [date], "notes": ""}
        rows.append(r); by[w] = r; changes.append(f"new word: {w}")
    for w, note in p.get("notes", {}).items():
        if w in by and note and note not in by[w]["notes"]:
            by[w]["notes"] = (by[w]["notes"] + f" {date[:5]}: {note}").strip()
    for r in rows: r["dates"] = sorted(set(r["dates"]), key=d)
    stage = lambda n: "Activated" if n >= 6 else "In Progress" if n >= 3 else "Emerging" if n else "Not Yet Observed"
    ups = [f'{r["word"]} -> {stage(len(r["dates"]))}' for r in rows
           if r["word"] in before and stage(len(r["dates"])) != stage(before[r["word"]])]
    doc["as_of"] = date
    json.dump(doc, open(out, "w"), ensure_ascii=False)
    print(json.dumps({"changes": changes, "stage_ups": ups, "total_words": len(rows)}, indent=1))

if __name__ == "__main__":
    main(*sys.argv[1:5])
```

<!-- file: phave_link.py -->
```python
#!/usr/bin/env python3
"""
Link new phrasal verbs to the native core (meta/phave) so the Native core panel stays honest.

For each word in the session's pv.new_words: if it starts with one of the 150 core phrasal
verbs (first word compared by its base form, so "went on with" -> "go on"), add it to that core
item's `rows`. The longest matching core verb wins. Different verbs that only look like
variants never link: "get up to", "get in touch with", "hold on to".

Writes phave_out.json only when something changed (it then goes into Step 6's single save).

Usage: python3 phave_link.py meta/phave.json session_doc.json phave_out.json
"""
import json, os, sys
import spacy

nlp = spacy.load("en_core_web_sm")
NEVER = {"get up to", "get in touch with", "hold on to"}
IRREG = {"got": "get", "took": "take", "came": "come", "went": "go", "gave": "give", "held": "hold",
         "kept": "keep", "brought": "bring", "ran": "run", "put": "put", "set": "set", "made": "make",
         "found": "find", "left": "leave", "thought": "think", "told": "tell", "stood": "stand"}

def base(first):
    w = first.lower()
    return IRREG.get(w) or nlp(w)[0].lemma_.lower()

def main(phave_path, sess_path, out):
    ph = json.load(open(phave_path)); ph = ph.get("data", ph)
    s = json.load(open(sess_path)); s = s.get("data", s)
    new = (s.get("pv") or {}).get("new_words", [])
    items = ph["items"]
    changes = []
    for w in new:
        toks = w.lower().replace("(", " ").replace(")", " ").split()
        if not toks or w.lower() in NEVER or any(w.lower().startswith(n) for n in NEVER): continue
        toks = [base(toks[0])] + toks[1:]
        best = None
        for it in items:
            core = it["word"].lower().split()
            if toks[:len(core)] == core and (best is None or len(core) > len(best["word"].split())):
                best = it
        if best and w not in best.setdefault("rows", []):
            best["rows"].append(w); changes.append(f'{w} -> core #{best["rank"]} {best["word"]}')
    if changes:
        json.dump(ph, open(out, "w"), ensure_ascii=False)
        print("linked:", "; ".join(changes), f"\nwrite {out} in Step 6")
    else:
        if os.path.exists(out): os.remove(out)
        print("no new core variants; meta/phave unchanged")

if __name__ == "__main__":
    main(*sys.argv[1:4])
```

<!-- file: lex_apply.py -->
```python
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
```

<!-- file: intf.py -->
```python
#!/usr/bin/env python3
"""
Turkish-interference side of the naturalness check (added 27.09.26).

Two blind passes (subagents, see "Interference pass instructions" in SKILL.md) each
write {"interference": [...], "upgrades": [...]}. This script:

  merge : unions the two passes (same turn + >=50% word overlap = one item, agree=2),
          checks every pattern key against meta/interference, and prints a REVIEW LIST
          (one-pass items and unknown pattern keys) for Claude to verify.
  apply : applies Claude's intf_verdicts.json, adds the "interference" block to
          session_doc.json, and writes meta_interference_out.json if new patterns were added.

Usage:
  python3 intf.py merge intf_A.json intf_B.json meta/interference.json intf_merged.json
  python3 intf.py apply intf_merged.json intf_verdicts.json meta/interference.json session_doc.json meta_interference_out.json

intf_verdicts.json:
  {"drop": [3, 17],                        # indices of merged items that are not interference
   "pattern": {"5": "by_the_way"},         # re-assign an item's pattern key
   "upgrade_drop": [2],                    # upgrade suggestions that are not useful
   "new_patterns": [{"key": "...", "label": "...", "turkish": "...", "type": "...", "fix": "..."}]}
Voice "missing_article" items count only when that pattern occurs 2+ times in voice in the
session (the transcriber can drop small words); single ones are kept but not counted.
"""
import json, re, sys

tok = lambda s: set(re.findall(r"[a-z']+", s.lower()))
T = lambda t: str(t).lstrip("T")
RANK = {"high": 3, "medium": 2, "low": 1}

def same(a, b):
    if T(a["turn"]) != T(b["turn"]): return False
    ta, tb = tok(a["quote"]), tok(b["quote"])
    return len(ta & tb) / max(1, min(len(ta), len(tb))) >= 0.5

def union(ia, ib, interf):
    used, out = set(), []
    for a in ia:
        m = next((j for j, b in enumerate(ib) if j not in used and same(a, b)), None)
        if m is None:
            out.append(dict(a, agree=1)); continue
        used.add(m); b = ib[m]
        best = a if RANK.get(a.get("confidence"), 0) >= RANK.get(b.get("confidence"), 0) else b
        x = dict(best, agree=2)
        if interf and a.get("pattern") != b.get("pattern"):
            x["pattern_alt"] = b.get("pattern") if x is a else a.get("pattern")
        out.append(x)
    out += [dict(b, agree=1) for j, b in enumerate(ib) if j not in used]
    for x in out: x["turn"] = "T" + T(x["turn"])
    out.sort(key=lambda x: int(T(x["turn"])))
    return out

def merge(pa, pb, metap, out):
    A, B, meta = json.load(open(pa)), json.load(open(pb)), json.load(open(metap))
    keys = {p["key"] for p in meta["patterns"]}
    items = union(A["interference"], B["interference"], True)
    ups = union(A.get("upgrades", []), B.get("upgrades", []), False)
    for i, x in enumerate(items): x["i"] = i
    for i, x in enumerate(ups): x["i"] = i
    json.dump({"interference": items, "upgrades": ups}, open(out, "w"), indent=1, ensure_ascii=False)
    both = sum(x["agree"] == 2 for x in items)
    print(f"interference: A {len(A['interference'])} · B {len(B['interference'])} · union {len(items)} · both passes {both}")
    print(f"upgrades: {len(ups)}")
    print("REVIEW LIST  (index | agree | pattern | type | quote -> fix)   [only one-pass items, unknown keys and key disagreements]")
    for x in items:
        unk = x.get("pattern") not in keys
        if x["agree"] == 1 or unk or x.get("pattern_alt"):
            flag = ("UNKNOWN KEY " if unk else "") + (f"alt={x['pattern_alt']} " if x.get("pattern_alt") else "")
            print(f'{x["i"]:4} | {x["agree"]} | {x.get("pattern")} {flag}| {x["type"]} | {x["turn"]} {x["mode"][0]}: {x["quote"][:90]} -> {x.get("fix","")[:50]}')
    print("UPGRADES  (index | quote -> suggestion)")
    for u in ups:
        print(f'{u["i"]:4} | {u["turn"]} {u["mode"][0]}: {u["quote"][:80]} -> {u.get("suggestion","")[:60]}')

def apply(mp, vp, metap, sp, metaout):
    M, v, meta, doc = json.load(open(mp)), json.load(open(vp)), json.load(open(metap)), json.load(open(sp))
    drop = set(int(i) for i in v.get("drop", []))
    re_p = {int(k): p for k, p in v.get("pattern", {}).items()}
    udrop = set(int(i) for i in v.get("upgrade_drop", []))
    known = {p["key"] for p in meta["patterns"]}
    added = [p for p in v.get("new_patterns", []) if p["key"] not in known]
    meta["patterns"] += added; known |= {p["key"] for p in added}
    pmap = {p["key"]: p for p in meta["patterns"]}
    W = {m: doc["by_mode"][m]["words"] for m in ("voice", "typed")}
    items = []
    for x in M["interference"]:
        if x["i"] in drop: continue
        k = re_p.get(x["i"], x.get("pattern"))
        if k not in known:
            sys.exit(f'item {x["i"]} has unknown pattern "{k}": map it in "pattern" or add it to "new_patterns"')
        items.append({"turn": x["turn"], "mode": x["mode"], "quote": x["quote"][:300], "pattern": k, "type": pmap[k]["type"],
                      "turkish": x.get("turkish_source", "")[:120], "fix": x.get("fix", "")[:200],
                      "confidence": x.get("confidence"), "agree": x["agree"]})
    va = [x for x in items if x["pattern"] == "missing_article" and x["mode"] == "voice"]
    for x in items: x["counted"] = not (x in va and len(va) < 2)
    bm = {}
    for m in ("voice", "typed"):
        c = sum(1 for x in items if x["mode"] == m and x["counted"])
        bm[m] = {"words": W[m], "count": c, "per_100": round(c / W[m] * 100, 2) if W[m] else None}
    tot, words = bm["voice"]["count"] + bm["typed"]["count"], W["voice"] + W["typed"]
    ups = [{"turn": u["turn"], "mode": u["mode"], "quote": u["quote"][:300], "suggestion": u.get("suggestion", "")[:200],
            "why": u.get("why", "")[:200]} for u in M["upgrades"] if u["i"] not in udrop]
    doc["interference"] = {"method": "two blind passes, union, verified by Claude", "count": tot,
                           "per_100": round(tot / words * 100, 2) if words else None, "by_mode": bm, "items": items,
                           "upgrades": ups, "patterns_seen": sorted({x["pattern"] for x in items if x["counted"]})}
    json.dump(doc, open(sp, "w"), indent=1, ensure_ascii=False)
    if added:
        json.dump(meta, open(metaout, "w"), ensure_ascii=False)
    top = {}
    for x in items:
        if x["counted"]: top[x["pattern"]] = top.get(x["pattern"], 0) + 1
    print(json.dumps({"by_mode": bm, "upgrades": len(ups), "new_patterns": [p["key"] for p in added],
                      "top": sorted(top.items(), key=lambda z: -z[1])[:8]}, indent=1, ensure_ascii=False))
    if added: print(f"meta/interference changed: write {metaout} back with if_version")

if __name__ == "__main__":
    {"merge": merge, "apply": apply}[sys.argv[1]](*sys.argv[2:])
```

<!-- file: intf_instructions.md -->
```markdown
# Interference pass: instructions (naturalness check, Step 3b)

You are analysing the English of Murat, a Turkish native speaker (C1-level, finance director), from one practice session. The turns file named in your task has his turns, each headed `### T<n> [voice]` or `### T<n> [typed]`. Voice turns are speech-to-text transcripts: fillers (uh, um), repeats and false starts are normal speech, NOT errors. Ignore them.

Do NOT open any other file in /tmp/nc except your turns file, the pattern list and this instruction file. Do not look at another pass's output.

Go through EVERY turn, sentence by sentence, in order. Do not skim. Produce two kinds of findings:

## A. INTERFERENCE (counts toward his score)
A place where Turkish shaped his English and the result is wrong or clearly non-native. Every item MUST name the Turkish source (the Turkish word, phrase or grammar feature behind it). If you cannot name a concrete Turkish source, it is NOT interference: either skip it or, if it is only a less natural choice, put it under B.

Types (use exactly these ids):
- `lex_false_friend`: word chosen because of its Turkish equivalent's range (şans -> "chance" for luck; "open/close the light" from ışığı aç/kapa; "make sport" from spor yapmak).
- `calque_phrase`: a Turkish set phrase translated word for word ("in the meantime" meaning bu arada; "long story to short" from uzun lafın kısası; "according to me" from bana göre; "since three years" from üç yıldır).
- `collocation_transfer`: a verb/noun/adjective pairing copied from Turkish ("take a decision" is fine; "do a mistake" from hata yapmak; "give a break" from ara vermek where English says "take a break").
- `preposition_case`: a preposition chosen from a Turkish case ending or postposition (-e/-a -> "to", -de/-da -> "in/at", -den/-dan -> "from"; "discuss about" from hakkında konuşmak; "married with" from ile evli).
- `pro_drop`: a missing subject or object pronoun that Turkish would drop ("if genuinely need", "I like" with no object).
- `article`: a missing or extra article (Turkish has none). IN VOICE TURNS the transcriber may drop "a/the" itself, so flag a voice article item only if the gap is clear and set confidence to "low" unless the same pattern repeats in the session.
- `word_order`: Turkish order (verb-final, heavy pre-noun modifiers, adverb placement) producing non-native order.
- `structure_transfer`: a clause or sentence built on a Turkish template (sahip olmak -> "has this ledger its own..." as a question; -mış gibi; "it has been 3 years that"; tense/aspect choices driven by Turkish -iyor / -di / -miş, e.g. present continuous for a habit, "since" + present).
- `discourse_transfer`: Turkish discourse markers carried over as fillers where English would not use them: "how to say" / "how can I say" (nasıl desem), "yani" patterns. ("I mean" and "you know" alone are fine.) Murat has confirmed these are Turkish-driven for him. Never flag "let's say" (Murat's decision, 29.09.26: as a filler it is only mildly odd, and counting it added noise); at most list it as an upgrade.

The pattern list file holds every pattern already confirmed for Murat: flag every occurrence of those. Keep in mind: "let's say" is never flagged in any use; "in the meantime" is correct when it really means "meanwhile".

For each item: turn, mode, exact quote (the shortest span that shows it, taken verbatim from the file), type, turkish_source (the Turkish word/phrase/feature), fix (what a native would say), confidence ("high" / "medium" / "low"), a one-sentence why, and `pattern`: the `key` of the matching pattern in the pattern list file (read its `patterns`: key, label, turkish, type, fix). Prefer a specific key over an `other_*` key. If nothing fits, write `new: <short plain-English label>` and use the same label each time it recurs.

## B. UPGRADES (NOT counted, suggestions only)
Correct English that a native speaker would more likely say differently (a stronger collocation, a more idiomatic phrase, a more precise word). Only include clear, useful upgrades, not personal taste. Fields: turn, mode, quote, suggestion, why (one sentence). If a Turkish influence is plausible, you may name it in "why", but it stays an upgrade.

## Do NOT flag
- plain grammar slips with no Turkish link (wrong tense form like "built" for "build", subject-verb agreement, typos) unless a Turkish source is specific and clear;
- speech disfluencies, restarts, repeated words, unfinished sentences in voice;
- informal but natural English;
- things he quotes from others or words he is talking about (e.g. "is 'come up' on the tracker?");
- game moves: confirming or scoring Claude's guesses in a word game such as Taboo ("that's true", "correct", "yes, that's it"). Murat decided these are not interference, even when they match a pattern in the list.

## Output
Write ONLY a JSON file at the path given in your task, shaped:
{"interference": [ {turn, mode, quote, type, pattern, turkish_source, fix, confidence, why} ... ],
 "upgrades": [ {turn, mode, quote, suggestion, why} ... ]}
Keep items in turn order. Then reply with just the counts by type and the number of upgrades.
```