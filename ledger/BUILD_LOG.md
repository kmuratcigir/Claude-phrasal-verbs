# Fluency Ledger: build log

Started 12.10.2026 · Status: data in published files since 30.10 (live version id `1793380526-31f6`, version 55)

## Links
- **Ledger (the page):** https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK (private, capability `db`)
- **Chunk tracking plan (agreed 12.10):** https://claude.ai/artifact/Kmeozvrx9sSpppVH9cE7Gf
- **Prep quiz (sibling project):** `prep-quiz/` in this repo, https://claude.ai/artifact/TZebyGZWe6Mu6Xtmq4UpLy

## Files
| File | What it is |
|---|---|
| `data/meta_chunks.json` | The chunk list as written to `meta/chunks` (version 3, 12.10). Edit here, then write it back with `if_version`. |
| `ledger.html` | The page source, identical to live version `1792140980-ca44` (published 16.10; earlier the same day `1792140084-a3c6`; before that `1791808670-cc1f`, 12.10; the original was `1790860799-3eb9`). The publish wrapper (doctype, head, `</body></html>`) is stripped; the service adds it back on publish. |

## How to republish
1. Edit `ledger.html` in the repo, never a copy elsewhere.
2. Read the live artifact first (`Artifact action:"read"` with the URL). If its version is no longer `1792140980-ca44`, someone published in between: diff it against `ledger.html` and merge before going on.
3. Test against a **frozen** copy of the real db (the lesson from the prep quiz: the db returns frozen objects, so a page that mutates loaded data breaks).
4. Publish `ledger/ledger.html` with `url` = the Ledger URL. Don't pass `capabilities`; the stored `{db:{}}` carries over.

## Who writes to this page's data
Since 30.10.26 the data lives in **files published inside the artifact** (`data/index.json`,
`data/meta/<name>.json`, `data/sessions/<id>.json`, `data/reading/<id>.json`), not in its db. The db is a
frozen copy as of 29.10.26; the page falls back to it only if a version has no `data/index.json`.
The page only reads. Skills save by publishing just the changed files, checked first by `ledger.py stage`
(refuses any save that would drop a row, a date or a review), one approval each:
- **naturalness-check:** `sessions/<s_YYYYMMDD_chatid>` plus `meta/pv_tracker`, `meta/vocab_tracker`, `meta/interference`, `meta/phave`, `meta/registry`, `meta/lexicon`, `meta/overview`, `meta/prep_watch`.
- **reading-session:** `reading/<id>`. **vocab-session:** `meta/vocab_tracker`, `meta/pv_tracker`. **chunk-update:** `meta/chunks`.
- **mini-prompt-update** and **phrasal-verb-tracker** only read.

**Rule:** a page change must never require a schema change those skills don't know about. New data (for example `meta/chunks`) is added alongside, never by changing existing fields.

## Plan (from the chunk tracking plan)
1. ✅ Source into the repo (this commit).
2. ✅ Store the chunk list (`meta/chunks`, now version 3, 12.10). All nine open (tracked); focus c1 + s1.
3. ✅ Naturalness check counts correct uses of open chunks. Upload files in `skill-upload/` (Murat installed them 12.10). `skill/chunks.py` (find / apply / rolling, finders for all nine), `skill/tests/` (109 cases + rolling rule), wired into SKILL.md steps 3–8 (a `chunks` block in the session doc, same single save); Mini Prompt nudge added. **First real run 12.10** (`s_20261012_95aebda7`): chunks block and report section saved as designed; c1 0/1, c2 1/1, c3 7/10, c4 1/1, c5 0/3, s3 2/3, s1/s2/s4 none.
4. ✅ Chunks tab in the Ledger (published 12.10). Tiles (open, settled, schedule, uses in the last session), one card per open chunk (pooled last-12 accuracy against the 80% line, the 12 uses as squares split by session, last session's uses, latest slip), "Coming up" with draft dates, "Settled" with a slip-back flag. Reads `meta/chunks` and each session's `chunks` block; writes nothing. Tested with a frozen copy of the real db: no errors, the other six tabs render identical text to the old page, synthetic data gives the right pooled figures (10 of 12 = 83%, ready to settle), no sideways scroll at 390px in dark mode.
5. ✅ New quiz items for chunks 3–5 and grammar slices 1–4 (65 items, `prep-quiz/src/bank_chunks.js`, approved 12.10).
6. ✅ Chunk mode in the prep quiz (version 14, 12.10). It reads `chunks/state` from the quiz's own db; built-in default until step 7.
7. ✅ New skill `chunk-update` (`skill-upload/chunk-update/`, 12.10): shows status and evidence (`scripts/status.py`), changes `meta/chunks` only on Murat's word, and writes the quiz's `chunks/state` (`{open, focus, settled, as_of, source:"ledger"}`) in the same run (two approvals: two pages). The quiz's `chunks/state` was seeded on 12.10 with c1 + s1 open.
   Also 12.10: `chunks.py find` no longer stops when an open item has no finder; it counts the others and prints `NOT COUNTED`. Finders for all nine were added later on 12.10 (see below); all three skills re-uploaded by Murat on 12.10 and confirmed with "chunk status".

## `meta/chunks` schema
`{as_of, version, plan_url, rule:{target, window_uses, min_sessions, mode, caught_counts_as, text, changed}, practice_nudge, shared_rules[], statuses[], pauses[{from,to,label}], later[], items[]}`

**Settled rule (v2, 12.10):** the last 12 voice uses at 80%+, spread over at least 4 sessions. It replaced "80% in 4 sessions in a row with 3+ uses each" because one full session had only 1 chunk-1 use and no "yet".

Each item: `{id ("c1".."c5", "s1".."s4"), layer ("chunk" | "slice"), n, title, status ("open" | "settled"), focus (true | false), planned[{from,to}], difficulty, counts, correct[], wrong[], left_out[], examples[{wrong,right,yours}], words[]?, note?}`.
Murat changes statuses and adds items by hand ("let's update the chunks"); no skill changes statuses on its own.

## 12.10 (later): all nine tracked, focus first (Murat's decisions)
Murat pointed out that he wanted **all** chunks monitored from the start, because any of them can improve before its date; only c1 and s1 had been set up. Decisions:
1. Track all 9 from 12.10 (`status: "open"` for every item; `meta/chunks` version 3).
2. Quiz Chunk mode: focus about 70%, other tracked about 20%, settled about 10% (version 15; with nothing settled, focus is about 80%).
3. Mini Prompt nudges towards all tracked chunks, focus items first.
4. Any item settles under the same rule (12 uses, 80%, 4 sessions), whatever its dates; dates change only when Murat changes them.
5. Ledger: full cards for focus items, one compact row for each other tracked item ("Also tracked"), Settled list.
6. Chunk 3 is tracked as a rough count.
7. Token cost accepted (about +3,000–5,000 per wrap-up).
8. Built all at once on 12.10 so the skills are installed once.

Finders for c2–c5, s2–s4 added to `skill/chunks.py`; `skill/tests/cases.json` now has 109 cases (all pass). On the 10.10 session all nine finders gave 24 candidates; after 3 hand verdicts ("use X for -ing" set correct) the counts were c1 0/1, c2 1/1, c3 4/8 (rough), c4 0/1, c5 0/1, s1 none, s2 6/9, s3 1/1, s4 none. Fixed during that test: "sorry for…" was stripped as a filler; "as you just said" is now left out of s2; `(?-i:[A-Z])` for proper names under `re.I`; "when it comes to" isn't purpose.

## 16.10: Murat's comments on the page (published as `1792140084-a3c6`)
1. **Chunks tab:** every tracked item now gets a full card, like the focus ones ("Also tracked" and "Settled" are card grids; this replaces decision 5 of 12.10). Cards show the latest slip, then "Show N more examples" with the earlier slips (newest first) and the plan's examples. Long slips are cut to 3 lines; the full sentence is on hover. "Rough count" moved onto the card for c3.
2. **Stage = the matrix.** The Stage column in both trackers shows the stage from days used (Activated / In progress / Emerging / Not yet observed). The imported "Mastered" label (from Murat's Word file, `mastered` in `meta/vocab_tracker` and `list.mastered` in `meta/pv_tracker`) is no longer shown or used for sorting. The data is unchanged, so nothing the skills write had to change.
3. **Vocab list summary:** "140 mastered" became "N solid & active (x%)" from the signal (12, 4% on 16.10).
4. **Interference chart** (Naturalness): drawn at 960×240 like the MTLD chart, so it is no longer very tall at full width.
5. **Density chart** (Phrasal verbs): no value labels on the line (`noVals` option in `lineChart`); values show on hover.
6. Answered only (no change): the faded rows at the bottom of the Overview grid are mistakes whose main impact is "slip" (`tr.slip`, opacity .6), sorted last on purpose.
- **Tests (frozen copy of the real db, 23 sessions, 16.10):** no console errors on any tab at 1100px light and 390px dark; no sideways scroll; Overview, Grammar, Naturalness and Reading render the same text as before; the only text changes are the ones above. Density hover shows "1 Oct · 1 per 47".
- **Seen in the data, not changed:** several chunk uses store the whole turn as `sentence` (c2, c3, s2, s3), so a slip can be a 60-word passage. The naturalness check could store a short excerpt around the chunk instead.

## 16.10 (later, published as `1792140980-ca44`)
- **Mastered label: gone for good** (Murat: "we've started from scratch and keep it that way"). Don't bring it back; stages come only from the matrix.
- **Two accuracies on each chunk card:** the big number is the last 12 voice uses (the settle rule); under it "All uses since <first use>: x% · n uses in m sessions" (Murat asked for a year-to-date figure; counting only started 12.10, so for now it is "since the start"). `ckPool` returns `allAcc`, `allSess`, `since`.
- **Chunks left, slices right** in Focus, Also tracked and Settled (`.cksplit` with two `.ckcol` columns; one column under 820px, chunks first).
- Tests: frozen real db, no errors at 1100px and 390px, no sideways scroll.

## 16.10: Prepositions tab, agreed design (mockup https://claude.ai/artifact/8GoFrdXp9rJerSDqeMirVh, `mockups/prepositions-tab.html`)
Nothing built yet; build starts on Murat's go.
- **True accuracy in speech**, voice only. A new spaCy script in the naturalness check lists every word + preposition pair; a pair is wrong if the check flagged it, right otherwise. Dropped prepositions come from the flags. Infinitive "to" never counts. No new installs (spaCy already runs).
- **Watch list** (live): one row per word + preposition pair Murat has slipped on; every later use of that word counts, right or wrong. New slips add rows automatically. Seeded from the Ledger's past slips (353 pairs from 753 slips on 16.10).
- **Row key = the word he said**, not the word in the fix (Murat, 16.10). "bridge the holiday towards the weekend" → row *bridge*, the fix ("link it to the weekend") shown as an example.
- **Story by Turkish source**, 9 fixed groups: -e, için, time words, -de, ∅ no preposition, ile, hakkında, -den, unsorted. A row's group comes from the Turkish source the check records. New groups only on Murat's word.
- **Heatmap:** the quiz's 41 chips, true speaking accuracy, grey under 5 uses.
- Also: 2×2 "how each word is going", session dropdowns, "Show more" examples with fixes per row.
- Estimated cost: about 4,000–8,000 tokens per wrap-up (to be measured). The step fails softly: if it errors, the check says so and carries on.
- The tab reads only the Ledger; the quiz stays separate.

### 16.10.26 — Watch list seed and the second-slip rule
- Seed rebuilt from all 23 saved sessions (18.09–15.10): 245 words after hand merges and drops; 107 with 2+ slips go on the list, 138 one-slip words wait.
- Rule (Murat, 16.10.26): a word joins the list on its second slip. After one slip it waits (`status: "waiting"`), and its uses count only in the overall figure. Replaces the earlier "new word joins on first slip".
- preps.py: phrasal-verb keys (look back, look up), one `dates` row, count diff for the right preposition, no pronoun/filler keys; `score` returns `joined_list`, `new_waiting` and `watch_changes`.
- Review page: https://claude.ai/artifact/Muww9cTWwVvhv1Cy41R5N7 — approved by Murat 16.10.26 and saved as `meta/prep_watch` (version 1; 107 on the list, 138 waiting).

### 16.10.26 — Prepositions tab (version 54, id `1792154156-ea16`)
- New tab between Chunks and Reading. One session picker (Last 5 / All / each session) and one mode switch (Voice + typed / Voice / Typed) for the whole tab.
- Sections: four tiles (all prepositions, watch list, words on the list, weakest group with 10+ uses), two trend charts with voice and typed lines, the story by Turkish source (9 groups, watch-list accuracy, 80% line), the 41-chip heatmap (plus "also counted" chips outside the quiz list), the 2x2 grid (5+ uses, mockup rule), the watch list table with group filter and examples, the waiting words, how it is counted.
- Data: reads `meta/prep_watch` and `sessions/*.preps` only. `preps` = raw [right, uses] per mode for all, watch, groups, chips and each watch word, plus `seq` (R/W voice, r/w typed) per word.
- 15.10 backfilled from the full pasted chat with the check's own saved slips: 93% of 525 (voice 93% of 425, typed 94% of 100); watch list 82% of 131. Watch list not changed (those slips were already in the seed).
- Typed turns count too (Murat, 16.10.26), everywhere. preps.py: conjunctions and stray tags dropped from the pairs; unmatched slips still count as one wrong use.
- Known limit: a row is one word, so unrelated uses of the same word count too (e.g. "book" the noun under "book" the verb).
- Next: wire preps.py into the naturalness-check SKILL.md (fail softly, one save) and give Murat a zip.

### 16.10.26 — Naturalness check counts prepositions (zip given to Murat, not yet installed)
- `skill-upload/naturalness-check/`: `scripts/preps.py` added (twelve scripts); SKILL.md: intro paragraph, Step 1 reads `meta/prep_watch` and notes its version, Step 5 runs `preps.py run murat_turns.txt session_doc.json meta/prep_watch.json prep_watch_out.json <doc_id>` after `intf.py apply`, report gets `### Prepositions` under `## Turkish interference` (two lines), Step 7 adds `meta/prep_watch` to the single batch, Step 8 and voice mode mention it, Limits note.
- `preps.py run` reads the check's own slips from `session_doc.json` (interference `preposition_case` + `err_preposition`, same slip once), writes the `preps` block and `prep_watch_out.json`. Fails softly: prints `PREPS SKIPPED`, changes nothing, the check goes on. A second run in the same chat changes nothing twice (`log` per doc id in `meta/prep_watch`). Tested on the 15.10 doc: rerun identical; a broken watch file skips cleanly.
- `SKIP_KEYS` / `ALIAS` keep the hand-cleaning of the seed for new slips (no rows for "one", "year", "expensive"…; "rooted" → root).
- Next: Murat uploads the zip; review after the first real wrap-up (figures and real token cost).

### 30.10.26 — Data moved from the db into files (chats lost `ArtifactData`)
- **Why:** from 30.10 new chats have no `ArtifactData`, only `db_get`/`db_list`/`db_query`/`db_write`, which pass every document through the conversation. A wrap-up reads ~0.5 MB of meta docs plus ~3.4 MB of session docs: about a million tokens that way, so it could not work. Murat's test in a new chat showed the artifacts toolset's `read_file` saves a file straight into the workspace and `publish_files` publishes from it, so neither direction passes through the chat (checksums matched both ways).
- **Choice:** keep every doc exactly as it was, but as a published file inside the Ledger artifact. No reshaping, no trimming of history, no extra token cost beyond a few hundred tokens of tool summaries per file read. Rejected: splitting trackers into row docs with `db_*` merges (+80–110k tokens per wrap-up, needs a schema change and still retypes the session doc); running the check in Claude Code only (Murat wants it in the practice chat).
- **Backup** before any change: full db dump (`meta` 10 docs, `sessions` 28, `reading` 5) as `ledger_backup.json` in the Project (30.10), page version `1792154156-ea16`. Counts: pv_tracker 451, vocab_tracker 335, prep_watch 294, lexicon 3,234, interference 142, chunks 12.
- **Page:** the loader reads `data/index.json` and the files (same `doc().onSnapshot` / `collection().onSnapshot` shape, so nothing else changed); db fallback when no index. Test copy https://claude.ai/artifact/35xN1jsCinfhTYfCLwbdhz: all 8 tabs identical to the live page (Murat checked with Claude in Chrome: all 43 records, every number), no console errors.
- **Skills** (`skill-upload/`, all six that touch the ledger): a shared "The ledger's files" section (read with `read_file` / `Artifact read`, save with `publish_files` / `Artifact publish`, never `publish_version`), and `ledger.py` (`snapshot` after reading, `stage` before saving; in `scripts/` for naturalness-check and chunk-update, embedded for reading-session and vocab-session). chunk-update still writes the quiz's own small `chunks/state` db doc (`db_write` in chats). vocab-session publishes its quiz page with `publish_files` in chats. reading-session can no longer delete a reading log from a chat (Claude Code only).
- `reading-session` and `phrasal-verb-tracker` added to `skill-upload/` (copies of the installed skills, then edited).
- **Tested** on the copy: `ledger.py` refuses a lost row, a lost date and an unread existing session; a pretend 30.10 session through `pv_apply.py` + `vt_apply.py` staged and published 4 files (sizes match), page shows "29 sessions · last check 30 Oct". The `read_file`/`publish_files` route itself was tested only on a small file in a chat; the first real wrap-up is the full test.
- **Limit:** one version holds at most 511 files; with one session file a day that is about 15 months. Before then, fold old sessions into fewer files.
- Murat backed up the 8 installed skills (`skills_backup_29_10_2026.zip`, in the Project) and uploaded the six new ones (30.10).
- **Live switch, 30.10:** fresh db read identical to the backup (byte for byte, all 43 docs); published `ledger.html` + 44 data files as version 55 (`1793380526-31f6`); every file at its db size; capability `db` kept for the fallback.
- Next: first real run = the 30.10 session (`s_20261030_0aa5b852`) in a new Project chat; then measure the real token cost.

