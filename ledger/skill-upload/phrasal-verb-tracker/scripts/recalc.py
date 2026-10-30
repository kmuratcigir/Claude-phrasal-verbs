#!/usr/bin/env python3
"""
Recalculate the Phrasal Verb Activation Tracker's derived columns
(Come-up Count, Mastery Status, Recency Status, Overall Signal) from
raw come-up dates, and add today's come-ups / new words.

This exists so Claude never hand-computes the lookup matrix or the
recency windows -- both are easy to get subtly wrong by hand across
250+ rows, and this script makes them deterministic instead.

Usage:
    python3 recalc.py <tracker_in.json> <updates.json> <as_of DD.MM.YYYY> <tracker_out.json>

tracker_in.json: [{"word": "show up", "dates": ["03.09.2026", ...], "notes": "..."}, ...]
updates.json: {
    "come_ups": [{"word": "show up", "note_append": ""}, ...],   # words with a genuine come-up today
    "new_words": [{"word": "hash out", "note": ""}, ...]          # first-ever sighting today
}
as_of: today's date, DD.MM.YYYY -- recency is measured against this for EVERY row.

Writes tracker_out.json with every row's derived columns recalculated,
plus a summary of what changed (for Claude to report in its reply).
"""
import sys
import json
from datetime import datetime

MASTERY_BANDS = [
    (0, 0, "Not Yet Observed"),
    (1, 2, "Emerging"),
    (3, 5, "In Progress"),
    (6, float("inf"), "Activated"),
]

SIGNAL_MATRIX = {
    ("Activated", "Green"): "Solid & Active",
    ("Activated", "Yellow"): "Solid but Cooling",
    ("Activated", "Red"): "Fading Despite Strong Base",
    ("In Progress", "Green"): "Building Momentum",
    ("In Progress", "Yellow"): "Stalling",
    ("In Progress", "Red"): "At Risk",
    ("Emerging", "Green"): "Fresh Start",
    ("Emerging", "Yellow"): "Early Fade",
    ("Emerging", "Red"): "Lost Spark",
}


def parse_date(s):
    return datetime.strptime(s.strip(), "%d.%m.%Y")


def mastery_status(count):
    for lo, hi, label in MASTERY_BANDS:
        if lo <= count <= hi:
            return label
    return "Activated"


def recency_status(dates, as_of_dt):
    if not dates:
        return None
    most_recent = max(parse_date(d) for d in dates)
    elapsed = (as_of_dt - most_recent).days
    if elapsed < 0:
        raise ValueError(f"A come-up date is after as_of date ({most_recent} > {as_of_dt})")
    if elapsed <= 7:
        return "Green"
    if elapsed <= 14:
        return "Yellow"
    return "Red"


def overall_signal(mastery, recency):
    if mastery == "Not Yet Observed":
        return "—"  # em dash, matches existing tracker
    return SIGNAL_MATRIX[(mastery, recency)]


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)

    tracker_in_path, updates_path, as_of_str, tracker_out_path = sys.argv[1:5]

    with open(tracker_in_path) as f:
        rows = json.load(f)
    with open(updates_path) as f:
        updates = json.load(f)

    as_of_dt = parse_date(as_of_str)

    by_word = {r["word"]: r for r in rows}
    changes = []

    # 1. Add today's come-ups (append date only if not already logged today)
    for cu in updates.get("come_ups", []):
        word = cu["word"]
        if word not in by_word:
            raise ValueError(
                f"'{word}' marked as a come-up but not found in tracker -- "
                f"add it via new_words instead if this is its first sighting."
            )
        row = by_word[word]
        if as_of_str not in row.get("dates", []):
            row.setdefault("dates", []).append(as_of_str)
            changes.append(f"come-up: {word}")
        note_append = cu.get("note_append", "").strip()
        if note_append:
            row["notes"] = (row.get("notes", "").strip() + " " + note_append).strip()

    # 2. Add brand-new words, starting directly at Emerging with today's date
    for nw in updates.get("new_words", []):
        word = nw["word"]
        if word in by_word:
            raise ValueError(f"'{word}' listed as new but already exists in tracker.")
        row = {"word": word, "dates": [as_of_str], "notes": nw.get("note", "")}
        rows.append(row)
        by_word[word] = row
        changes.append(f"new word: {word}")

    # 3. Recalculate derived columns for EVERY row (recency drifts with time alone)
    for row in rows:
        dates = row.get("dates", [])
        # de-dupe while preserving order, sort chronologically
        seen = []
        for d in dates:
            if d not in seen:
                seen.append(d)
        seen.sort(key=parse_date)
        row["dates"] = seen

        count = len(seen)
        mastery = mastery_status(count)
        recency = recency_status(seen, as_of_dt)
        signal = overall_signal(mastery, recency) if recency else "—"

        row["count"] = count
        row["mastery"] = mastery
        row["recency"] = recency or ""
        row["signal"] = signal

    # Sort by Come-up Count descending (matches existing tracker convention),
    # ties broken alphabetically for stability
    rows.sort(key=lambda r: (-r["count"], r["word"].lower()))

    with open(tracker_out_path, "w") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(json.dumps({"changes": changes, "total_words": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
