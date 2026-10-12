# Fluency Ledger: build log

Started 12.10.2026 · Status: source copied into the repo, no changes made yet

## Links
- **Ledger (the page):** https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK (private, capability `db`)
- **Chunk tracking plan (agreed 12.10):** https://claude.ai/artifact/Kmeozvrx9sSpppVH9cE7Gf
- **Prep quiz (sibling project):** `prep-quiz/` in this repo, https://claude.ai/artifact/TZebyGZWe6Mu6Xtmq4UpLy

## Files
| File | What it is |
|---|---|
| `ledger.html` | The page source, identical to live version `1790860799-3eb9` (read 12.10). The publish wrapper (doctype, head, `</body></html>`) is stripped; the service adds it back on publish. |

## How to republish
1. Edit `ledger.html` in the repo, never a copy elsewhere.
2. Read the live artifact first (`Artifact action:"read"` with the URL). If its version is no longer `1790860799-3eb9`, someone published in between: diff it against `ledger.html` and merge before going on.
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
2. Store the chunk list (`meta/chunks`).
3. Naturalness check counts correct uses of open chunks; test on 2–3 past chats against a hand count.
4. Chunks tab in the Ledger.
5. New quiz items for chunks 3–5 and grammar slices 1–4.
6. Chunk mode in the prep quiz.
7. Step that copies chunk statuses into the quiz.
