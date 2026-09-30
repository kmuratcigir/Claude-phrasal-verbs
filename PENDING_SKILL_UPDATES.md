# Pending skill updates (on hold until Murat says go)

Agreed 30.09.2026 while building the Overview mock-up
(https://claude.ai/artifact/9znAHGRJd7xAVQkGALtfjE). Do NOT start until Murat gives the prompt.

## naturalness-check
1. Write the Overview brief to the ledger (`meta/overview`) in the existing Step 6 batch (keep ONE approval):
   headline + intro, three periods (Today / This week Mon-Sun vs last week / Since the start = last 3 vs first 3 sessions),
   each with a one-line verdict, 3-4 score lines (Better/Worse) chosen to fit that day's story, and +/− points with
   "quote → fix"; 3 priorities with an impact label and a said→should-say example; signature date.
   Tone: CEO report, frank both ways, few numbers, a story. Honesty rules: numbers only from session docs,
   say when method changes could explain a trend, small typed samples called small.
2. Label every mistake by impact, without asking Murat: `m` changes the meaning, `f` sounds foreign, `s` slip.
   Store per item (errors[].impact, interference.items[].impact). For grammar-list items, the correct/error
   ratio can back the call (≥80% correct → slip).
3. Lock the 29.09 text-report format into Step 7 (Murat liked it) AND save that day's report text to the
   session doc (e.g. sessions/<id>.report) so the Overview's "Session report" panel shows it. Latest session only.
4. Fallback when read_conversation is unavailable (29.09 problem).

   Backfill: all 468 past mistakes (9 sessions) were already labelled by hand for the mock-up
   (overview/impact_labels_18-29.09.json: [session index 0-8, concept, M/F/S] in the ledger error order); write them into the session docs when the tab goes live.

## mini-prompt-update
5. Same read_conversation fallback in Step 2.

## Other open items from the Build Log (0k C)
6. Vocab session saves in two writes; could be one batch.
7. Weekly backup prompt still checks obsolete meta/vocab_items → switch to vocab_tracker, add lexicon.

## Decided on the page side (no skill change needed)
- Grid rows use the ledger's technical names + a real example; picked automatically (A: most frequent in last 3
  sessions; B: 3 biggest risers + 3 biggest fallers). Both versions kept.
- Grid names link to Grammar (Well-used structures / Errors) or Naturalness (Interference patterns).
- First grid column = average of the first 3 sessions; Change = last 3 vs first 3; date columns slide (latest 6).

## Process when Murat says go
Read both installed SKILL.md files in full → write updated files → test on 29.09 data without saving →
send files → Murat saves them via a Project chat ("propose these as skill updates") → build the Overview tab
in the ledger, write the first brief (one approval) → next wrap-up is the real test.
