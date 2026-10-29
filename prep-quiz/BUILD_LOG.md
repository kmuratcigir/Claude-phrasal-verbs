# Prepositions & Collocations quiz: build log

Session date: 07.10.2026, updated 14.10 · Published versions: 1 to 17 · Status: working, in use

## Links
- **Quiz artifact (the page):** https://claude.ai/artifact/TZebyGZWe6Mu6Xtmq4UpLy (private, current version 17, id `1791970190-8813`)
- **Fluency Ledger (source of truth, read-only for this project so far):** https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK
- **Vocab quiz (style reference, never edited):** https://claude.ai/artifact/PkXEna9VTLyi2FDj4LDtD9

## Files in this folder
| File | What it is |
|---|---|
| `src/template.html` | Page layout, CSS and all logic. Has two placeholders, `/*__STATS__*/` and `/*__BANK__*/` |
| `src/bank.js` | Practice bank: 68 patterns (56 prepositions + 12 verb + noun), `EXTRA` new contexts, `PAIRS` contrast pairs |
| `src/bank_adv.js` | Challenge bank: 24 harder prepositions (`ADV`), `ADV_FAMILIES`, contrast-pair hints |
| `src/bank_topup.js` | `TOPUP`: 48 new-context items (12.10) so every pattern has at least 3. Loaded last |
| `src/bank_chunks.js` | `CHUNK_BANK` (7 patterns, sec `chunk`, 65 items: chunks 3–5 and grammar slices 1–4), `CHUNKS` (chunk → quiz patterns) and `CHUNK_DEFAULT`. Loaded last |
| `chunk-items-review.html` | The review page for those 65 items (approved 12.10) |
| `src/stats.js` | Speaking snapshot: `SESSIONS` (21 sessions, words) and `HITS` (slips per pattern per session), ledger as of 13.10 |
| `src/bank_feed.js` | `FEED_1310`: 26 "your sentence" items from 12.10 and 13.10 (approved 14.10). Loaded last |
| `src/stats_adv.js` | Speaking hits for Challenge patterns (`Object.assign(HITS, …)`) |
| `src/group.py` | The regex grouping used to sort ledger slips into patterns (reference; needs manual review) |
| `build.py` | Assembles `prep-quiz.html` from `src/`. Run it, then publish that file to the artifact URL |
| `prep-quiz.html` | Built page, identical to published version 17 |

To republish from a new thread: run `python3 prep-quiz/build.py`, read the artifact first (`Artifact action:"read"` with the URL), then publish `prep-quiz/prep-quiz.html` with `url` = the artifact URL. Don't pass `capabilities`; the stored `{db:{}}` carries over.

## Data sources (Step 1 analysis)
- Ledger `sessions` (15 docs, 18.09 to 06.10): `interference.items` of type `preposition_case` (344) and `collocation_transfer` (77), plus `errors` with concept `err_preposition` (133) and `err_collocation` (216).
- Errors that matched an interference item in the same session were dropped, which left **642 records**.
- 163 items sit in the ledger's catch-all `other_preposition`, so about 40% of the grouping is Claude's judgement (marked ⚑ in the original table).
- Out of scope: phrasal-verb misuse (it has its own PV quiz) and about 40 one-off word-choice slips.

## What the page does
**Tabs:** Practice | Challenge | Progress

**Practice tab**
- **Auto pick:** last 5 speaking sessions (3 × hits), due reviews (+4), last-time misses (+3), plus 1–2 "quiet checks". Default 20 items, then it reuses the last size.
- **Choose myself:** picker grouped into 12 preposition families. Quick buttons: active, due (n), weak (n), least practised groups.
- **Mix setting:** 100/75/50/25/0 % your sentences vs new contexts. Default 50/50. It is exact: tested 80/0, 40/40, 0/80.
- **Verb + noun collocations:** optional, off by default.

**Challenge tab**
- 24 harder prepositions in 3 groups: path, multi-word, position.
- The mix setting does not apply here. Only 10 of its 71 items are the user's sentences.
- Its own size setting (default 15) and its own session slot.

**Item formats**
- Fill-in-the-blank (about 70%) with a `∅ no preposition` button.
- Multiple choice (about 30%). Distractors are only the user's real wrong forms.
- Fix-my-sentence, with a "Mine means the same" override.
- Contrast pairs: 18, each pair two blanks with per-blank ∅ buttons.

**Hints**
- Level 1 shows the pattern label plus the trap. Pairs get their own hint covering both sentences.
- Level 2 gives the first letter; level 3 the first two letters.
- A correct answer after a hint counts as a review but doesn't move the pattern up.

**Answering**
- An empty Check reveals the answer and counts as a miss.
- Each item is labelled "your sentence · date" or "new context".
- The pattern label stays hidden until hint 1 or the answer.

**Which sentence comes up (12.10):** oldest first. Within the kind the mix asks for, items are ranked by when they were last answered (from `history`) or served (from `seen`), never-seen first; one is picked at random from the 1–3 oldest, so the order can't be memorised.

**Spacing:** per pattern, Leitner intervals 1 → 3 → 7 → 14 → 30 days. A miss goes back to the start (due tomorrow).

**Progress tab**
- **Scores:** Practice and Challenge separately (last 30 answers, hint = half).
- **Performance heatmap:** chips, sorted weakest first, amber to green. Three tabs: Speaking / Quiz / **Combined 70% speaking + 30% quiz**. Prepositions (41 chips) on top, collocations (8 verb chips) underneath.
  - Speaking % = 100 − 100 × slips per 1,000 words in the last 5 sessions, floored at 0.
  - A chip stays grey until it has at least 3 slips on record.
  - ·q = quiet, ·s = speaking only, ·z = quiz only.
- **2×2 grid:** speaking trend (Rising / Steady / Fading / Quiet) against quiz strength. Needs 3 answers per pattern.
- **Pattern groups table:** sparklines, expandable groups, Challenge rows included.

**Trend rule:** Rising needs at least 3 recent hits and ≥ 1.5× the earlier rate. Fading needs ≤ 0.5×. Quiet means no hits in the last 5 sessions (unproven).

## Quiz memory (artifact db, capability `db`)
- `patterns/<key>` = `{k, box, due:"YYYY-MM-DD", reviews, last, history:[{t, ok, hint, fmt, item, src, gaveUp}], seen:[item idx], label, sec}`. `sec` is one of `prep`, `vn` or `adv`.
- `runs/<r_timestamp>` = `{tab:"core"|"adv", mode, size, started, updated, kind:"review", answered, correct, hinted, items:[…]}`.
- `settings/prefs` = `{size, vn, mix, advSize}`.
- Unfinished sessions are kept in localStorage (`ppq_session_core`, `ppq_session_adv`), one per tab.
- **Item indices are stable.** New items are always appended, never inserted, so saved `seen` and `history` stay valid. Keep it that way.
- At handoff the memory held the user's first sessions (07.10). Read it with `ArtifactData list` on `patterns` and `runs`.

## Bugs found and fixed (lessons for the next thread)
1. **Check did nothing (v2 to v3).** The db returns **frozen objects**, so `history.push` threw. Fix: deep-clone everything loaded from the db (`JSON.parse(JSON.stringify(v))`). **Test with a frozen fake db** loaded through a real page navigation (`page.route` + `goto`); `setContent` skips init scripts.
2. Check now reads the input from the DOM, not from cached state.
3. Fixes once went into the built file instead of the template. **Always edit `src/`, then build.**
4. The mix drifted because freshness was preferred over the requested kind. Fixed: pick by kind first, then by freshness.
5. Starting a Challenge session wiped the Practice session. Fixed with one session per tab.

## User's standing rules
- The user chooses the mix and the size. Auto only runs when the user presses it.
- Only the user adds items to study lists. Practice counts as a review, never as a use.
- Use the user's real sentences (cleaned of fillers), labelled with their date. Never invent "the user's" mistakes; new sentences are labelled "new context".
- Distractors are the user's own wrong forms. Every answer has a "why" and a Turkish source; general (non-ledger) mappings are labelled as such.
- Be honest about thin data. Ask one question at a time. Keep the vocab-quiz visual style (light theme, purple accent).
- Don't write to the ledger yet; ledger integration is on hold.

## Known limitations
- The speaking data is a **static snapshot (13.10)** built into the page.
- "towards" and "out from" hits are counted in both Practice and Challenge patterns.
- The ledger records slips only, so Speaking % is a stand-in, not an accuracy.
- Comment threads on the page can't be replied to or resolved by Claude unless the user sends them to Claude.

## Next step (open discussion)
**Feeding the quiz from new ledger sessions.** Claude's proposal is a skill, not an unattended agent, run at wrap-up or on request:
1. Read the new ledger sessions (read-only).
2. Sort the slips into patterns; put unclear ones under "unsorted".
3. Show the user the proposed new "your sentence" items for approval.
4. Write the approved changes to the quiz db.

Prerequisite: the page must read the speaking snapshot and extra items from its db (for example `speech/snapshot` and `items_extra/*`) instead of from built-in code, so updates need no republish.

**Decision (14.10): parked.** No feed skill for now; the naturalness check is already complex enough. The feed stays manual: when Murat asks, Claude reads the new Ledger sessions, sorts the slips by hand, proposes items for approval, then rebuilds and publishes (see "14.10 manual feed" below for the method). Revisit later.

## Parked (07.10): merge all practices into a Ledger "Practice" tab?
The user raised merging the three quizzes (prep quiz, phrasal verb quiz, irregular verb drill) into the Fluency Ledger under a new **Practice** tab. **Decision parked; the user is sleeping on it.** Nothing was built or changed.

What was found:
- **Ledger:** one published page, about 166 KB / 2,141 lines, plain JS, `db` collections `sessions` and `reading`. Its source is **not** in the repo.
- **Phrasal verb quiz** (Claude Design, React): about 5,000 lines, mostly a built-in verb dataset (about 450 KB). Progress lives in browser storage (`pvq_*` keys) and is pushed to this repo (`data/phrasal-verb-db.json`, `data/lookup-verbs.json`, branch `main`). Its "targeted" mode means verbs are pasted in by hand. **Security: its code contains a hard-coded GitHub token (`DEFAULT_GH_TOKEN`). The user was told to revoke it. Never commit that file while the token is in it.**
- **Irregular verb drill** (Claude Design, React): small (about 430 lines plus 6 KB of verb data), browser storage only (`irregularVerbStats_v1`), no link to the Ledger, and the Ledger has no irregular-verb field.

Claude's assessment:
- **Feed cost:** merging removes the speaking snapshot, because the quiz would read `sessions` live, and lets the phrasal verb quiz pick verbs from the Ledger automatically. The judgement step (sorting slips, approving items) stays the same.
- **Risk:** the code wouldn't change daily, only the data. The risks are one much bigger page to read and edit, a quiz bug breaking the dashboard that four skills write to, and a React-to-plain-JS rewrite.
- **Coherence:** one place, one style, one progress view. This is a real gain.
- **Progress:** both Design quizzes keep results in that browser's storage, so moving them needs a one-off export.
- **Suggested order if the user says yes:** revoke the token → put the Ledger source in the repo with a build step → prep quiz first → phrasal verb quiz → irregular drill last.
- **Next question for the user:** does the irregular drill's saved history matter, or can it start fresh?

## 12.10 update (published as version 13)
- **Speaking snapshot to 10.10.** 07.10 is the hand-sorted column from the 07.10 thread. 08.10, 09.10 and 10.10 were sorted by Claude (regex from `group.py`, then each slip checked by hand). One-off word-choice slips and phrasal-verb misuse are left out as before.
- **Top-up rule (agreed 12.10):** every pattern keeps at least 3 new-context items. Whenever the feed adds the user's sentences, it also checks the pattern's new-context count and proposes enough to reach 3; brand-new patterns get 3. Each new item changes the frame (subject, tense, question/negative, position, topic), not just the noun.
- **Why:** the mix is applied per session, so adding the user's sentences never breaks the ratio. The real risk was repetition: 46 patterns had only 1–2 new contexts, so the user would memorise sentences rather than the pattern.
- The river item ("rose ___ its normal level") accepts "above" or "over", at the user's request.
- **Tests:** frozen fake db with the real 12.10 `patterns` data. 0 existing items moved, 48 added. Mix exact at 0, 50 and 75%. Oldest-first: no repeats back-to-back; with 6 items over 40 picks, each came up 5–8 times. A full session saved without errors.
- **Possible new patterns seen in 08.10–10.10, not in the quiz yet:** "the first time" with no preposition (4: in/at the first time), "evolve into" (3), "apologise to me" (3), "on the right track" (2), "at dinner" (2).

## 12.10 update 2 (published as version 14): Chunk mode
- New **Chunks** tab (Practice | Challenge | Chunks | Progress). Auto pick shares the session evenly between the open chunks (due reviews and last-time misses first); settled chunks get about 20% as review. "Choose myself" practises any chunk. Uses the Practice mix setting.
- Chunk 1 and chunk 2 reuse existing patterns (see `CHUNKS` in `bank_chunks.js`); the others use the new `ch_*` patterns. Patterns with sec `chunk` are kept out of Practice auto pick, the picker, the heatmap and the 2×2 grid (`isCore` excludes them). Progress has a third score box, "Chunks".
- **Which chunks are open** comes from this quiz's db doc `chunks/state` = `{open:[ids], settled:[ids], as_of, source:"ledger"}`. Until step 7 writes it, the built-in `CHUNK_DEFAULT` (c1 and s1 open, as of 12.10) is used. The quiz never writes it, and quiz results never go to the Ledger.
- c4 items use the ∅ button (`zero:true` on the pattern, label "∅ nothing").
- **Tests (frozen real db):** 0 existing items moved; Practice auto pick never served a chunk pattern (30 runs × 40 items); chunk sessions split c1/s1 8/7 at size 15 and kept the 50% mix (0.53); a 15-item chunk session saved patterns and a `runs` doc with tab `chunk`; a fake `chunks/state` (c1 + c4 open, s1 settled) gave c1/c4 sessions with 2 s1 review items; manual c3 session served only `ch_c3_purpose`; no sideways scroll at 390px dark; no console errors.
- Fixed before publishing: a chunk with a single pattern was capped at 6 items per session.

## Version 15 (12.10)
Chunk mode split: focus about 70%, other tracked about 20%, settled about 10% (see `ledger/BUILD_LOG.md`).

## 13.10 update (published as version 16): chunk heatmap + recommendations
Murat's comment on the Progress tab (13.10): a chunk-specific heatmap showing the parts (committed / dedicated to, on my list, put effort into / invest in, add / set, add / save to, and "paste into", which went back to the start), plus recommendations: what's going well and what to focus on.
- New **Chunk heatmap** card on Progress, right under Scores (`renderChunkHeatmap` in `template.html`). One row per chunk/slice (focus first, then tracked, then settled, with a tag), one chip per quiz pattern. Chip % = the last 10 answers (hint = half), same colour scale as the main heatmap; ↺ = back to the start (box 0); faded with "· n" when fewer than 3 answers; grey "—" = not practised. Tooltip: %, answers, hints, last 5 (✓ / h / ✗), review step and next date.
- **What's going well:** 5+ answers, 80%+, at least step 2. **What to focus on:** 3+ answers and either back to the start or under 75%; adds "the last 5 were all right, so it is improving" when true. Focus chunks are listed first, at most 4 per list. A line lists tracked chunks with no practice yet.
- **Quiz only.** Speaking accuracy for chunks is on the Ledger's Chunks tab; the card says so. The page still writes nothing new.
- **Tests (frozen copy of the real db, 13.10):** no console errors; no sideways scroll at 390px; Practice, Challenge, Chunks and Progress render the same text as version 15 apart from the new card; no db writes from opening Progress. On 13.10 data: going well = on my list, committed / dedicated to, add / set; focus = paste into (↺), invest in (70%, improving), "yet" (70%, improving), join / contact / message (↺, 50%). Not practised yet: c3, c4, c5, s3, s4.
- Fixed before publishing: chips with a single answer from 07.10 (responsible for 0%, mention / discuss 50%) had full colour and reached the focus list.

## 14.10 manual feed (published as version 17)
Murat asked for a manual feed this time (the skill is still to be designed).
- **Snapshot to 13.10:** sessions 12.10 (4,953 words) and 13.10 (3,984) added to `SESSIONS` / `HITS` / adv hits. Slips sorted by hand, as for 08–10.10: interference items of type preposition_case / collocation_transfer plus `err_preposition` / `err_collocation` errors not already in interference; phrasal-verb misuse and one-off word choices left out.
  - 12.10: sense_of 1 (⚑ "outcome from"), confused_about 1, add_to 2, ask_sb_q 1, over_time 2, same_about 1, for_me 2, time_duration 1, save_for 1, rooted_in 1, adv_among_between 1, adv_along 1.
  - 13.10: time_duration 1, no_prep_verbs 3, save_for 1, same_about 1, of_not_for 1, confused_about 1, wait_for 1, key_to 2, dates_times 1, for_me 1, put_add 1, add_to 1, on_device 1, over_time 1, on_my_list 1, vn_decision 1 (⚑ "make a mistake", no item), adv_along 1.
  - Judgement calls: "important for me" not counted (it is correct English); "moving onto the wrap-up" not counted (the Ledger did not flag it); "turns to" was listed twice in interference for one utterance and counted once.
- **26 new "your sentence" items** in `src/bank_feed.js` (22 + 4 extras, all approved by Murat 14.10), appended after all existing items.
- **Tests (frozen real db):** 0 existing items moved, 26 added; every new answer accepted and none of its distractors; manual sessions over the fed patterns served new items 28% of the time at 100% "yours"; a 30-item session answered and saved (60 writes) with no errors; Progress shows "speaking data as of 13.10 · 21 sessions"; no sideways scroll at 390px.
- **Unsorted, possible new patterns (not added):** turn into / evolve into (1 + 3 earlier), stay over with us / at ours (2), "-e karşı" said as "against" for with / towards (2), late for a meeting (1), plus single slips: look back on, recommended to me, open to, read → look at my notes, from time to time, than (comparative -den), a question about.

## 29.10 grammar slices 5–7 (built and tested, version 18 not yet published)
`chunks/state` already listed s5, s6 and s7 as open (since 29.10), but they had no items, so Chunk mode skipped them.
- **21 new items, all new contexts (N)**, 7 per slice, in `src/bank_chunks.js` as three new patterns appended after `CHUNK_BANK` (`CHUNK_BANK_2910`), so no existing item index moves. Samples approved by Murat 29.10, then the rest written.
  - `ch_s5_ever` (s5, "ever / never" for life experience): never been to Norway, ever tried Turkish coffee, daughter never flown alone, never seen a deal like this in twenty years in finance, ever been to Japan, never eaten sushi before, ever driven in İzmir traffic.
  - `ch_s6_sofar` (s6, "so far / up to now / until now"): three meetings so far today, nothing has gone wrong with the audit, daughter has passed two of five exams, 40% of the budget spent so far, the new system hasn't given trouble, two days of rain on this trip, everything has gone to plan until now (halfway through the review).
  - `ch_s7_thisweek` (s7, "this week / month / year", "lately"): two books this month ("it's only the 15th"), busy lately, two clients signed this year ("two months to go"), daughter's new friends this term ("only half-term"), İzmir prices gone up lately, not slept well this week ("the audit doesn't finish until Friday"), heard from the bank lately.
- **Rules kept:** one right answer per item (full and short forms both accepted); no "left out" case is ever a wrong answer (no finished time, habits, future, set phrases, distance, plans, "this morning / today", "until then", "know / realise until now"); "until now" only where the situation clearly goes on; every s7 period is clearly still running, so the British past simple can't be argued for.
- `CHUNKS` gets s5–s7 with their keys, so the picker, auto plan and heatmap know them.
- **Tests (frozen copy of the real quiz db, 29.10):** 0 existing items moved, 21 added, pattern order unchanged; every accepted answer passes and no distractor does; a 21-item manual session over s5–s7 (7 multiple choice, 14 typed) answered right = 21/21 and saved (42 writes); the same items answered with their wrong option = 0/21 accepted; auto Chunk sessions now include s5–s7 (5–6 picks each over 20 sessions of 15); no console errors; no sideways scroll at 390px and 900px on the Chunks start page and in a session; Progress opens without errors.
