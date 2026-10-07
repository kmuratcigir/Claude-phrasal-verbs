# Prepositions & Collocations quiz: build log

Session date: 07.10.2026 · Published versions: 1 to 12 · Status: working, in use

## Links
- **Quiz artifact (the page):** https://claude.ai/artifact/TZebyGZWe6Mu6Xtmq4UpLy (private, current version 12)
- **Fluency Ledger (source of truth, read-only for this project so far):** https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK
- **Vocab quiz (style reference, never edited):** https://claude.ai/artifact/PkXEna9VTLyi2FDj4LDtD9

## Files in this folder
| File | What it is |
|---|---|
| `src/template.html` | Page layout, CSS and all logic. Has two placeholders, `/*__STATS__*/` and `/*__BANK__*/` |
| `src/bank.js` | Practice bank: 68 patterns (56 prepositions + 12 verb + noun), `EXTRA` new contexts, `PAIRS` contrast pairs |
| `src/bank_adv.js` | Challenge bank: 24 harder prepositions (`ADV`), `ADV_FAMILIES`, contrast-pair hints |
| `src/stats.js` | Speaking snapshot: `SESSIONS` (15 sessions, words) and `HITS` (slips per pattern per session), ledger as of 06.10 |
| `src/stats_adv.js` | Speaking hits for Challenge patterns (`Object.assign(HITS, …)`) |
| `src/group.py` | The regex grouping used to sort ledger slips into patterns (reference; needs manual review) |
| `build.py` | Assembles `prep-quiz.html` from `src/`. Run it, then publish that file to the artifact URL |
| `prep-quiz.html` | Built page, identical to published version 12 |

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
- The speaking data is a **static snapshot (06.10)** built into the page.
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

**Open question to the user:** should the feed run automatically as the last step of wrap-up, or only when asked?
