# Fluency Ledger: build log

Started 12.10.2026 · Status: Chunks tab live (version id `1791806356-4a32`, 12.10)

## Links
- **Ledger (the page):** https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK (private, capability `db`)
- **Chunk tracking plan (agreed 12.10):** https://claude.ai/artifact/Kmeozvrx9sSpppVH9cE7Gf
- **Prep quiz (sibling project):** `prep-quiz/` in this repo, https://claude.ai/artifact/TZebyGZWe6Mu6Xtmq4UpLy

## Files
| File | What it is |
|---|---|
| `data/meta_chunks.json` | The chunk list as written to `meta/chunks` (version 1, 12.10). Edit here, then write it back with `if_version`. |
| `ledger.html` | The page source, identical to live version `1791806356-4a32` (published 12.10; the original was `1790860799-3eb9`). The publish wrapper (doctype, head, `</body></html>`) is stripped; the service adds it back on publish. |

## How to republish
1. Edit `ledger.html` in the repo, never a copy elsewhere.
2. Read the live artifact first (`Artifact action:"read"` with the URL). If its version is no longer `1791806356-4a32`, someone published in between: diff it against `ledger.html` and merge before going on.
3. Test against a **frozen** copy of the real db (the lesson from the prep quiz: the db returns frozen objects, so a page that mutates loaded data breaks).
4. Publish `ledger/ledger.html` with `url` = the Ledger URL. Don't pass `capabilities`; the stored `{db:{}}` carries over.

## Who writes to this page's db
The page only reads. Skills write, each in one approval:
- **naturalness-check:** `sessions/<s_YYYYMMDD_chatid>` plus `meta/pv_tracker`, `meta/vocab_tracker`, `meta/interference`, `meta/phave`, `meta/registry`, `meta/lexicon`, `meta/overview`.
- **reading-session:** the `reading` collection.
- **vocab-session**, **mini-prompt-update** and **phrasal-verb-tracker** read or update the trackers above.

**Rule:** a page change must never require a schema change those skills don't know about. New data (for example `meta/chunks`) is added alongside, never by changing existing fields.

## Plan (from the chunk tracking plan)
1. ✅ Source into the repo (this commit).
2. ✅ Store the chunk list (`meta/chunks`, now version 2, 12.10). Open: chunk 1 and slice 1; the rest not started.
3. ✅ Naturalness check counts correct uses of open chunks. Upload files in `skill-upload/` (Murat installed them 12.10). **Built 12.10:** `skill/chunks.py` (finders for c1 and s1), `skill/tests/` (26/26). Tested on the 10.10 session, which Murat pasted in: it matched a hand count (c1: 1 voice use, wrong; 1 typed use, correct; no "yet"). Still to do: wire it into the skill (SKILL.md steps 3–5, a `chunks` block in the session doc, the same single save), and add the practice nudge to the Mini Prompt.
4. ✅ Chunks tab in the Ledger (published 12.10). Tiles (open, settled, schedule, uses in the last session), one card per open chunk (pooled last-12 accuracy against the 80% line, the 12 uses as squares split by session, last session's uses, latest slip), "Coming up" with draft dates, "Settled" with a slip-back flag. Reads `meta/chunks` and each session's `chunks` block; writes nothing. Tested with a frozen copy of the real db: no errors, the other six tabs render identical text to the old page, synthetic data gives the right pooled figures (10 of 12 = 83%, ready to settle), no sideways scroll at 390px in dark mode.
5. ✅ New quiz items for chunks 3–5 and grammar slices 1–4 (65 items, `prep-quiz/src/bank_chunks.js`, approved 12.10).
6. ✅ Chunk mode in the prep quiz (version 14, 12.10). It reads `chunks/state` from the quiz's own db; built-in default until step 7.
7. Step that copies chunk statuses into the quiz.

## `meta/chunks` schema
`{as_of, version, plan_url, rule:{target, window_uses, min_sessions, mode, caught_counts_as, text, changed}, practice_nudge, shared_rules[], statuses[], pauses[{from,to,label}], later[], items[]}`

**Settled rule (v2, 12.10):** the last 12 voice uses at 80%+, spread over at least 4 sessions. It replaced "80% in 4 sessions in a row with 3+ uses each" because one full session had only 1 chunk-1 use and no "yet".

Each item: `{id ("c1".."c5", "s1".."s4"), layer ("chunk" | "slice"), n, title, status ("not_started" | "open" | "settled"), planned[{from,to}], difficulty, counts, correct[], wrong[], left_out[], examples[{wrong,right,yours}], words[]?, note?}`.
Murat changes statuses and adds items by hand ("let's update the chunks"); no skill changes statuses on its own.
