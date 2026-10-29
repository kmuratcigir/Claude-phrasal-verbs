---
name: "fixing-slot"
description: "Run Murat's fixing slot: a short spoken drill on 1-3 grammar targets, corrected live, wrapped in marks so the naturalness check keeps only those targets out. Trigger on \"fixing slot\", \"grammar drill\", \"grammar practice\"."
---

# Fixing slot

Built 29.10.26 with Murat. The fixing slot is **fixing time**, kept apart from **speaking time**:
he says a few real sentences aloud on his current targets, and only those targets are corrected,
live and briefly. Everything else in the chat stays free speaking, with no live flags (the slips go
into the pattern map at the end, as agreed on 28.10).

Standing rules, from Murat:
- He starts it, any time in the session (start, middle or end), in any words: "fixing slot",
  "grammar drill", "grammar practice", "let's do a drill", "drill starts" and the like.
- He chooses the targets. Claude never adds one on its own; it may suggest, he confirms.
- One question at a time. In voice mode every turn is short, no recaps.
- About 10 minutes is the usual length; he decides when it ends.

## The marks

Two fixed marks, said exactly like this, each at the very start of Claude's message:
- **"Fixing slot starts."** in the first message of the drill;
- **"Fixing slot ends."** in the message after Murat says, in any words, that he is done
  ("let's finish", "let's end the drill", "that's enough").

Never close the slot on a guess. If he drifts into free conversation without saying it's over, ask
once: "Shall we close the fixing slot?" If the slot stops and starts again later, use a new pair of
marks each time. The vocab session has its own marks ("Vocab drill starts." / "Vocab drill ends.");
the two are never mixed.

**What the naturalness check does with them:** only the drilled targets, and only between these
marks, are kept out of the chunk counts. Everything else between the marks (other grammar,
prepositions, vocabulary, phrasal verbs, interference) is judged as normal, and every use of a
target outside the marks counts as a real use.

## Step 1: Confirm the targets

Start with "Fixing slot starts." and the targets in one short line, e.g. "Today: I've already,
and I still have. Shall we go?" The current targets are in the Mini Prompt (Section 6, "THE NEW
SYSTEM"). If none are listed, or he wants a change, ask which ones. One to three targets.

Each target is tied to a chunk id, so the check knows what to keep out:

| Target (what he says) | Chunk |
|---|---|
| I've already / I've just + past participle | s2 |
| haven't ... yet | s1 |
| I still have / I've still got | c5 |
| for / since (still going on) | s4 |
| ever / never | s5 |
| so far / up to now / until now | s6 |
| this week / month / year, lately | s7 |
| add / put ... to (not into) | c1 |
| mention / discuss (no "about"), ask (no "to") | c2 |
| to, not "for + -ing", for purpose | c3 |
| no "a" before uncountables | c4 |
| finished time → past simple | s3 |

A target not in this table, or a chunk not yet open in the Ledger (s5-s7 until they are added), is
fine to drill; tell him in one line that the check can't count it yet.

## Step 2: The drill

1. Give a short real prompt from his life that invites the target (his day, work, the trip, Yaz),
   e.g. "What have you already done today?" or "What do you still have to do before London?"
   Don't model the sentence for him first.
2. He answers aloud in real sentences.
3. Reply in one line: if every target use was right, say so briefly ("Right."); if not, "X → Y",
   nothing more. Correct **only the targets**; leave every other slip alone.
4. Next prompt, mixing the targets. Vary the topics; never repeat a prompt in the same slot.
5. Ask before correcting anything that could be a transcription error ("I've already get" may be
   the transcriber, not him).

## Step 3: Close the slot

When he says he's done, start the next message with "Fixing slot ends." and give one line:

**Slot result:** I've already 6/6 · I still have 3/5

(right uses / all uses of each target inside the slot, from the chat; a self-correction made at once
counts as half, the standing rule). Then say nothing more about the slot; free speaking follows.

Also write one more line, which the naturalness check reads:

**Drilled targets:** s2, c5

## What this skill never does

- No ledger writes. The naturalness check records everything at the end of the session.
- No live flags outside the slot, praise included.
- No drill he didn't start.