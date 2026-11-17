# English Mastery scores: design note (agreed 02.11.2026)

Status: built 02.11.2026 (see BUILD_LOG.md, entry 02.11.26, for what was built and the two changes).
Mockup (sample + real data): https://claude.ai/artifact/91uJNJ36rrYKQ34LwuWAA6
Ledger: https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK

## 1. What gets built
One "English Mastery" card on the Overview tab, placed after the trend charts. It shows three areas (Grammar, Vocabulary, Speaking), each with a ring /100, its parts, the change since the last session and a trend chart. A Daily / Cumulative switch and a Voice / Typed / Combined switch apply to the whole card.
Remove from the Overview only: the "Accuracy and Turkish patterns, voice" graph and the "Range: advanced words (B2+)" graph. Their data and tabs stay.
Grammar and vocabulary concept details appear on the Overview card only. No new cards go on other tabs.

## 2. Principles
- Raw counts are stored per session. The page calculates every score, daily and cumulative. No score is stored.
- Settings live in one doc (`meta/scoring`). Changing a setting recalculates the whole history.
- Cumulative = totals added up first, then divided. Never an average of daily scores.
- Voice and typed are scored separately. Combined = weighted by word count. Speaking = voice only.
- Preply figures stay in the Mini Prompt only, never in the Ledger.
- Scripts do the counting. The model reads only where judgement is needed (see section 7).

## 3. Speaking (voice only)
Score = average of 4 sub-scores. Each sub-score maps linearly between its 0 point and its 100 point and is clipped to 0–100.

| Measure | Definition | 0 pts | 100 pts |
|---|---|---|---|
| Flow | clean words per reply | 5 | 30 * |
| Depth | % of replies that develop an idea | 40% | 90% |
| Cohesion | linking connectors per 100 clean words (long list) | 4 | 14 (cap) |
| Fillers | uh/um + word fillers per 100 words (lower is better) | 15 | 2 |

- Clean words = words minus uh/um, word fillers, immediate repeats and abandoned restarts.
- Replies with fewer than 3 clean words are left out of Flow and Depth.
- Cohesion: count a connector only when it joins two ideas. A reply-initial run-up "so/and" doesn't count. The card also shows the number of different connectors used.
- Drills: nothing is left out. Slot answers are real speaking.
- Restarts and "losing track" are parked as separate measures. Restarts are still removed from clean words.
- \* CALIBRATE BEFORE LOCKING: a voice "reply" in our transcripts is a whole turn, often 60+ words, while Preply's reply is shorter. The 02.11 prototype gave Flow 63.7 on sample turns, which would sit above the 100 point every day. See step 3 in section 8. Same check for Cohesion: the prototype gave 13.6 because "so" and "actually" are counted too often.

## 4. Grammar
Grammar = (Accuracy + Range) ÷ 2. Accuracy = (Concept mastery + Grammar-clean sentences) ÷ 2.
- Concept mastery: for each concept in `meta/registry` (84 non-error concepts), correct ÷ uses over its last 12 uses. Reach back by whole sessions. The minimum is 5 uses. Weighted average by level: A1–A2 ×1, B1 ×2, B2 ×3, C1 ×4, C2 ×5. Cumulative view = all uses.
- Grammar-clean sentences: the share of sentences with no grammar error. Grammar = ERRANT types PREP, DET, VERB:SVA, VERB:TENSE, VERB:FORM, VERB:INFL, NOUN:NUM, NOUN:INFL, PRON, WO, PART when not a phrasal verb, MORPH, CONJ. Word-choice types go to Vocabulary (section 5).
- Range: the level-weighted share of the 84 concepts used correctly in the last 5 sessions (cumulative: ever). Show next to it the plain count ("49 of 84, 58%") and a "share of score" column per level.
- Not using a concept lowers Range, never Accuracy.
- Drills: only the drilled targets between "Fixing slot starts/ends" are left out. Everything else in the slot counts.
- Reference (30.10, real data): mastery 94, clean 90 → accuracy 92; range 49 → Grammar 71. Cumulative 10.10–30.10: 74.

## 5. Vocabulary
Vocabulary = (Range + Reuse + Accuracy) ÷ 3.
- Range: the B2+ share of the different words used, weighted B2 ×1, C1 ×1.33, C2 ×1.67. 20% = 100.
- Reuse: the share of the day's B2+ words that were already used in an earlier session (look back to 18.09). Cumulative: the share of all B2+ words used in 2+ sessions. Shown beside it, not scored: list words that came up unprompted.
- Accuracy: word-choice problem points per 100 words, where 0 = 100 and 2 = 0.
  - Problems = the union of word-choice slips (ERRANT R:NOUN, R:VERB, R:ADJ, R:ADV, R:PART for phrasal verbs, and R:OTHER when lexical) and Turkish word-choice interference (types lex_false_friend, calque_phrase, collocation_transfer). Each problem counts once.
  - Points: 1 per problem, 3 if meaning-changing (impact `m`).
- Drills: only the drilled words between "Vocab drill starts/ends" are left out. Practising a word never counts as reuse. Reading never counts as use.
- Reference (30.10): range 50, reuse 62, accuracy 62 → Vocabulary 58. Cumulative 10.10–30.10: 43 (reuse understated, because only data from 10.10 was loaded).

## 6. Raw counts to add to each session doc (new block `mastery`)
```
mastery: {
  speaking: {replies, short_replies, words, clean_words, developed, connectors, connector_types[], hesitations, word_fillers, repeats, repairs},
  grammar: {voice:{concepts:{id:{c,e}}, sentences, grammar_err_sentences}, typed:{...}, drilled_excluded:[...]},
  vocab:   {voice:{unique, b2, c1, c2, adv_words[], lex_problems, lex_m, words}, typed:{...}, drilled_excluded:[...]},
  method: "v1 02.11.26"
}
```
Concept counts must be split into voice and typed. Today they are pooled. Each error gets an `errant` type field.

## 7. Tooling (researched 02.11.26) and the token plan
Script-based, no model tokens:
- spaCy (already used): clauses, connector check (dep cc/mark/advmod with a verb head), sentence split.
- Regex: hesitations (uh, um, er, erm, hmm, mm), word fillers, immediate 1–3-word repeats, "sorry" repairs. The 02.11 prototype ran in under 1 s.
- **ERRANT** (pip `errant`, uses spaCy): types each error from its quote→fix pair. That makes the grammar/vocabulary split automatic. Tested 02.11 on his errors: turn off→down = R:PART; narrow→limited = R:ADJ; doing→making = R:VERB; was→were = R:VERB:SVA; for→to + "a" dropped = R:PREP + U:DET; discuss about = U:PREP; have still→still have = R:WO; regret to try→trying = R:VERB:FORM. Known weak spot: "we've asked→we asked" came out as R:OTHER. Review R:OTHER items only.
- Connector list: start from the PDTB 100 connectives / DiMLex-Eng (149) plus his tracked items.
- Depth: rule first. Developed = 10+ clean words AND 2+ finite clauses. Validate it once against a judged pass on 2 past sessions. Keep the rule if it agrees about 85%+ of the time. Otherwise judge it inside the existing interference passes (one extra label per turn) instead of a separate pass.

Looked at and not adopted: cefrpy (frequency-based levels beyond CEFR-J, "monkfish = C2"); LanguageTool (Java server, likely too many false flags on speech); GECToR / BERT disfluency models (torch and Hugging Face downloads not available); TAACO / TAALES / TAASSC (desktop tools); POLKE (external API, detects presence not correctness).

Extra tokens per wrap-up, target: about 5–10k. No new subagent passes.

## 8. Build order (Claude Code)
1. Sync the repo with the installed skills (naturalness-check, vocab-session, fixing-slot, chunk-update, mini-prompt-update).
2. Add `scripts/mastery.py` to naturalness-check: speaking counts + ERRANT typing + vocab problem union. Save the `mastery` block in the Step 6 batch (still one approval).
3. Calibrate the Speaking settings on the last 5 sessions with transcripts. Set the 0 and 100 points so the median day scores about 50, and validate the Depth rule.
4. Create `meta/scoring` (all settings above, version-stamped).
5. Build the Overview card from the mockup and remove the two graphs. Check desktop + phone, light + dark, and that the other tabs are unchanged.
6. Backfill grammar and vocab `mastery` blocks from existing session docs (sentence counts exist only from 28.10). Speaking starts at the next wrap-up.
7. Update mini-prompt-update so Section 4 shows Grammar / Vocabulary / Speaking, daily and cumulative.
8. Murat installs the updated skills in Claude (same versions in chat and Claude Code). Add a Build_Log entry.
