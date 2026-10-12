# Interference pass: instructions (naturalness check, Step 3b)

You are analysing the English of Murat, a Turkish native speaker (C1-level, finance director), from one practice session. The turns file named in your task has his turns, each headed `### T<n> [voice]` or `### T<n> [typed]`. Voice turns are speech-to-text transcripts: fillers (uh, um), repeats and false starts are normal speech, NOT errors. Ignore them.

Do NOT open any other file in /tmp/nc except your turns file, the pattern list and this instruction file. Do not look at another pass's output.

Go through EVERY turn, sentence by sentence, in order. Do not skim. Produce two kinds of findings:

## A. INTERFERENCE (counts toward his score)
A place where Turkish shaped his English and the result is wrong or clearly non-native. Every item MUST name the Turkish source (the Turkish word, phrase or grammar feature behind it). If you cannot name a concrete Turkish source, it is NOT interference: either skip it or, if it is only a less natural choice, put it under B.

Types (use exactly these ids):
- `lex_false_friend`: word chosen because of its Turkish equivalent's range (şans -> "chance" for luck; "open/close the light" from ışığı aç/kapa; "make sport" from spor yapmak).
- `calque_phrase`: a Turkish set phrase translated word for word ("in the meantime" meaning bu arada; "long story to short" from uzun lafın kısası; "according to me" from bana göre; "since three years" from üç yıldır).
- `collocation_transfer`: a verb/noun/adjective pairing copied from Turkish ("take a decision" is fine; "do a mistake" from hata yapmak; "give a break" from ara vermek where English says "take a break").
- `preposition_case`: a preposition chosen from a Turkish case ending or postposition (-e/-a -> "to", -de/-da -> "in/at", -den/-dan -> "from"; "discuss about" from hakkında konuşmak; "married with" from ile evli).
- `pro_drop`: a missing subject or object pronoun that Turkish would drop ("if genuinely need", "I like" with no object).
- `article`: a missing or extra article (Turkish has none). IN VOICE TURNS the transcriber may drop "a/the" itself, so flag a voice article item only if the gap is clear and set confidence to "low" unless the same pattern repeats in the session.
- `word_order`: Turkish order (verb-final, heavy pre-noun modifiers, adverb placement) producing non-native order.
- `structure_transfer`: a clause or sentence built on a Turkish template (sahip olmak -> "has this ledger its own..." as a question; -mış gibi; "it has been 3 years that"; tense/aspect choices driven by Turkish -iyor / -di / -miş, e.g. present continuous for a habit, "since" + present).
- `discourse_transfer`: Turkish discourse markers carried over as fillers where English would not use them: "how to say" / "how can I say" (nasıl desem), "yani" patterns. ("I mean" and "you know" alone are fine.) Murat has confirmed these are Turkish-driven for him. Never flag "let's say" (Murat's decision, 29.09.26: as a filler it is only mildly odd, and counting it added noise); at most list it as an upgrade.

The pattern list file holds every pattern already confirmed for Murat: flag every occurrence of those. Keep in mind: "let's say" is never flagged in any use; "in the meantime" is correct when it really means "meanwhile".

For each item: turn, mode, exact quote (the shortest span that shows it, taken verbatim from the file), type, turkish_source (the Turkish word/phrase/feature), fix (what a native would say), confidence ("high" / "medium" / "low"), a one-sentence why, and `pattern`: the `key` of the matching pattern in the pattern list file (read its `patterns`: key, label, turkish, type, fix). Prefer a specific key over an `other_*` key. If nothing fits, write `new: <short plain-English label>` and use the same label each time it recurs.

## B. UPGRADES (NOT counted, suggestions only)
Correct English that a native speaker would more likely say differently (a stronger collocation, a more idiomatic phrase, a more precise word). Only include clear, useful upgrades, not personal taste. Fields: turn, mode, quote, suggestion, why (one sentence). If a Turkish influence is plausible, you may name it in "why", but it stays an upgrade.

## Do NOT flag
- plain grammar slips with no Turkish link (wrong tense form like "built" for "build", subject-verb agreement, typos) unless a Turkish source is specific and clear;
- speech disfluencies, restarts, repeated words, unfinished sentences in voice;
- informal but natural English;
- things he quotes from others or words he is talking about (e.g. "is 'come up' on the tracker?");
- plain scoring words in a game ("correct", "yes, that's it", "next one"). But DO flag a game reply that carries a Turkish pattern, such as "that's true" for "that's right" (doğru), every time it occurs: Claude counts the repeats once.

## Output
Write ONLY a JSON file at the path given in your task, shaped:
{"interference": [ {turn, mode, quote, type, pattern, turkish_source, fix, confidence, why} ... ],
 "upgrades": [ {turn, mode, quote, suggestion, why} ... ]}
If he corrects an item right away (says the right form straight after, or flags it with "sorry"), still flag it and add `"caught": true`.
Keep items in turn order. Then reply with just the counts by type and the number of upgrades.
