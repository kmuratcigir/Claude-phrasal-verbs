Paste this into a new Claude Code session on kmuratcigir/claude-phrasal-verbs:

---

I'm continuing work on my English-practice tools (project "My English Journey"). Repo `kmuratcigir/claude-phrasal-verbs`, branch `claude/preposition-collocation-quiz-jrzj1a`.

**Read first, fully:** `ledger/BUILD_LOG.md`, then `prep-quiz/BUILD_LOG.md`. They hold the design, the data schemas, my decisions and the publishing rules.

**Links**
- Fluency Ledger (dashboard; skills write to its db): https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK
- Prepositions & Collocations quiz (version 15): https://claude.ai/artifact/TZebyGZWe6Mu6Xtmq4UpLy
- Chunk tracking plan: https://claude.ai/artifact/Kmeozvrx9sSpppVH9cE7Gf
- Chunk quiz items review page: https://claude.ai/artifact/X71Y7mbcfwUisGom5YSC4C

**Where things stand (12.10)**
- New chunk system is live and was confirmed in a real wrap-up on 12.10: 5 chunks (c1–c5) + 4 grammar slices (s1–s4), all tracked every session; focus = c1 ("to/into" after add, put, paste, devote) and s1 ("yet" → present perfect). Settled = last 12 voice uses at 80%+ over at least 4 sessions, any item, any time. The dates are only a guide.
- The list lives in the Ledger's db `meta/chunks` (v3); the quiz has its own copy in `chunks/state`. Skills I installed on 12.10: `naturalness-check` (counts chunk uses with `scripts/chunks.py`), `mini-prompt-update` (nudges practice towards the chunks, focus first), `chunk-update` (shows status; changes the list only on my word). Their sources are in `ledger/skill-upload/`; the counting code and tests are in `ledger/skill/`.
- Ledger Chunks tab: focus cards + "Also tracked" rows + Settled. Quiz Chunk mode: focus ~70%, other tracked ~20%, settled ~10%.
- First counted session (12.10): c1 0/1, c2 1/1, c3 7/10 (rough), c4 1/1, c5 0/3 ("have still"), s3 2/3, s1/s2/s4 none.

**Still open**
- The quiz feed: how new sentences from my sessions become "your sentence" quiz items (a skill step, with my approval). We haven't decided it yet; the chunk work may have changed what it needs.
- Watch the next few wrap-ups: do the chunk counts look right? Is chunk 3 too rough to be useful?

**Rules that matter**
- Edit sources, never built files: `prep-quiz/src/` then `python3 prep-quiz/build.py`; `ledger/ledger.html`. Quiz items are appended, never inserted, so my saved history stays valid.
- Test pages against a frozen copy of the real db before publishing; read the live artifact before publishing over it.
- You can't install skills or read my project chats from Claude Code: give me zips to upload, and ask me to paste chat text when a test needs it.
- How I like to work: one question at a time, short and simple answers, honest about limits, decisions point by point with your recommendation. Don't build until I say go.

Start by telling me in a few lines what you understood, then ask what I want to do first.
