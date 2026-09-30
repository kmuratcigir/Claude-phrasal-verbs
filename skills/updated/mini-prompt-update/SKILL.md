---
name: "mini-prompt-update"
description: "End-of-session wrap-up for Murat's English practice: runs the naturalness check (logged to the Fluency Ledger) and then rebuilds the Mini Prompt from the ledger's numbers. Trigger on \"wrap up the session\", \"let's wrap up\", \"update the wrap-up files\", \"update the mini prompt\" or \"end of session update\" in My English Journey."
---

# Wrap up the session: naturalness check + Mini Prompt

Murat starts every new chat in this project by pasting a Mini Prompt: a single text block
carrying context forward (work/family situation, recent breakthroughs, stats, recent session
summaries, status of the supportive systems) so a fresh chat isn't starting from zero.

Since 26.09.26 the end of a session is one chain, started by one phrase ("wrap up the
session", or the older "update the wrap-up files" / "update the mini prompt" / "end of
session update"):

1. the **naturalness check** measures the chat and logs it to the Fluency Ledger (grammar,
   vocabulary, MTLD, phrasal verbs; the phrasal verb tracker now lives in the ledger and is
   updated by the check). Since 30.09.26 it also labels every mistake by impact, saves the day's
   report and rewrites the brief on the ledger's Overview tab, all in its one save;
2. this skill then rebuilds the **Mini Prompt**, taking every statistic from the ledger's
   session document instead of estimating it.

Dashboard: https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK ("Fluency Ledger").

## Trigger discipline

- One trigger, one run of each step. Don't also fire `phrasal-verb-tracker`: that skill is
  export-only now (it makes the tracker .docx on request) and the tracker update happens
  inside the naturalness check.
- "Naturalness check" on its own still runs only the check, not the Mini Prompt.
- Not mid-session: only when Murat is closing the session.

## Step 0: Make sure this chat's session is in the ledger

The session document id is `s_<YYYYMMDD>_<first 8 chars of this chat's id>` (the chat id is
in the URL `read_conversation` returns; the date is the practice day).

- If Murat already ran "naturalness check" in this chat **and there has been no real practice
  since** (only housekeeping messages), reuse it: `ArtifactData` `get` `sessions/<doc_id>`.
- Otherwise (the usual case) **run the `naturalness-check` skill now, in full**, following
  all its steps, including verifying every flag and writing the session and tracker to the
  ledger. Running it again in the same chat replaces that chat's session document, so a
  second run after more practice is safe. Leave the wrap-up trigger message out of Murat's
  words, the same as the check's own trigger message.

Give Murat the check's report as its Step 8 describes (text chat format), then continue to
Step 1 without waiting.

**One approval (28.09.26).** Murat has to approve every write to the ledger, with no
"always allow". The naturalness check saves everything, native-core links, the day's report and
the Overview brief included (`phave_link.py` replaced the separate PHaVE step here), in one
`batch` call. This skill writes nothing to the ledger itself: from here on it only reads
(`list` `sessions`, `list` `reading`) and delivers the Mini Prompt as a file.

## Step 1: Get the base to update

The Mini Prompt is not a project file. It lives only in the chat, carried forward by Murat.
Look for it in this order, and don't stop at the first miss:

1. **An attached file on the very first message of this thread.** Usually a `.docx`, `.pdf`,
   or `.txt` whose name contains "mini prompt" (case-insensitive; e.g.
   `MINI_PROMPT_23.09.2026.pdf`). Check the first message's attachments specifically. Read it
   with the tool that matches its format to get the actual text.
2. **Plain text pasted into the first message**, if no matching file is attached.
3. **Only if neither is present**, say so plainly and ask Murat to attach or paste the last
   Mini Prompt he has. Don't fabricate a starting point, and don't treat an unrelated
   attachment (vocab file, tracker, anything without "mini prompt" in the name) as the Mini
   Prompt.

## Step 2: Know the whole session

The Mini Prompt summarises the whole chat, Claude's side included, so the naturalness
check's file of Murat's words isn't enough on its own. If the chat has been compacted, the
check in Step 0 has just paged through it with `read_conversation`; use those pages while
they are still in context rather than reading again. Only if they're gone (or Step 0
reused an earlier check) page through `read_conversation` (`conversation_id: "current"`)
yourself. Never write the summary from the compacted remainder alone.

**If `read_conversation` isn't available (added 30.09.26;** it happened on 29.09.26**):** if the chat
was never compacted (you can see it from its very first message), write the summary from your
context and say so in one line when you deliver. If it was compacted, or you can't be sure, don't
guess the missing part: tell Murat plainly and ask him to paste or attach the earlier part of the
chat (his side and Claude's), then continue. The naturalness check in Step 0 follows the same rule.

## Step 3: Update all six sections

The Mini Prompt always has exactly these six sections, and **every one must be written out in
full**, never "[preserved]" or "[unchanged]". A placeholder is indistinguishable from content
that was forgotten; writing it out every time is the only way Murat can trust what he pastes.

1. **Work, Social and Family Context**: changes often; keep moderately detailed and current.
   Compress only material older than 3–4 days if the whole document is over budget (Step 5).
2. **Real-World Application & Native Speaker Practice**: major applications and
   native-speaker sessions. Same compression rule as Section 1.
3. **Key Insights & Breakthrough Patterns**: detailed and current. **Never compress.**
4. **Session Management & Statistics** (a SNAPSHOT since 28.09.26; the full figures live in
   the Fluency Ledger, so don't copy them here): at most about 8 lines.
   - One line pointing to the dashboard for details.
   - One line per day for the last 3 calendar days (combine a day's parts; a day with no
     session document is "not measured", never guessed): words analysed; errors per 100
     words, voice and typed separately; Turkish interference per 100 (voice); phrasal verb
     density ("1 per N words", native 1 per 192); grammar range "x / N" (N from
     `meta/registry`). Take every number from the ledger's session documents (`list` the
     `sessions` collection), never from estimates or from the old Mini Prompt.
   - One honest trend line (e.g. "voice errors up three sessions running; partly
     measurement") when the numbers show one.
   No per-day error lists, B2+ shares, MTLD or older-day summaries here: they are on the
   dashboard.
5. **Recent Sessions**: last 3–4 days in full detail; days 5–14 in 2–3 sentences each;
   anything older than 14 days removed.
6. **Supportive System Tracking** ("what to watch live" since 28.09.26): only what should
   change how Claude behaves in the next chat, at most about 15 lines. The come-up lists,
   stage-ups, tracker counts and Native core numbers live in the ledger; don't copy them here.
   - **Flag live**: the top 3–5 recurring error or Turkish-interference patterns from the
     last few session documents, each with the natural fix (e.g. "in the meantime" for "by
     the way" → "by the way"). These are what Claude should flag, lightly, every time.
   - **Close to a breakthrough**: at most 5 list words or phrasal verbs that got a stage-up
     or a first unprompted use in the last 3 days (from the check's output), so Claude can
     create natural chances to use them. No full lists.
   - **Vocab sessions**: the date of the last one and its practised words (the vocab-session
     skill's "Practised words:" line), in one line.
   - **Reading**: one line from the ledger's `reading` collection (`ArtifactData` `list`
     `reading`): date and title of the last passage, readings this week (Monday to Sunday)
     against Murat's target of 4. Don't list the words it contained; the Reading tab shows
     them and whether he later used them.
   - **Open items**: shadowing, Taboo and any other system thread that is waiting on Murat,
     one line each, only if still open.
   The formal writing practice system and the "never touched" phrasal verb list were removed
   on 28.09.26: drop any mention of them carried over from an older Mini Prompt, in any
   section, and don't add them back.

## Step 4: Information priority (if something has to give)

1. **Highest**: English Journey: breakthroughs, strategy changes, insights.
2. **Secondary**: personal context, major life events.
3. **Tertiary**: work context that affects practice, not every work detail.

Embed new information into the existing structure rather than inventing sections, and don't
repeat the same fact across sections without reason.

## Step 5: Length budget

Target **under 20,000 words**. Check the count before finalising.
- Under 20,000: keep everything per Step 3.
- Over 20,000: compress Sections 1 and 2 first (focus on the last 3–4 days); then Section 5
  moderately, trimming prose around the facts, not the facts. Section 3 is never
  compressed; Sections 4 and 6 are already short by design.

## Step 6: Quality check before delivering

- All 6 sections fully written out (highest-priority check).
- Under 20,000 words; Section 4 about 8 lines and Section 6 about 15 lines at most.
- Every number in Section 4 matches the ledger's session documents (spot-check at least
  today's figures against the check's `session_doc.json`).
- No stats or tracker lists copied into Sections 4 or 6 beyond the snapshot above; no
  writing-practice or "never touched" mentions anywhere.
- No fact repeated across sections without reason.

## Step 7: Deliver

Save as `MINI_PROMPT_<DD.MM.YYYY>.txt` (today's date) and send it to Murat with
`SendUserFile`. It is a file he pastes into his next chat, not a Project file; don't write it
anywhere else. In the same response, briefly:

1. Point back to the naturalness check report above (don't repeat it) and give the dashboard
   link.
2. Confirm the Mini Prompt file is ready, with one line on anything compressed or dropped.
3. Remind Murat to paste it at the start of his next session.

The phrasal verb tracker .docx is not produced in a wrap-up. If Murat wants the file, the
`phrasal-verb-tracker` skill exports it from the ledger on request.