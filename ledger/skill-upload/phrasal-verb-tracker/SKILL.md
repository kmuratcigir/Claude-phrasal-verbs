---
name: "phrasal-verb-tracker"
description: "Export Murat's Phrasal Verb Activation Tracker as a .docx file from the Fluency Ledger, where the tracker now lives. Use when Murat asks for the tracker file, the tracker .docx, or an export of the phrasal verb tracker, in My English Journey. Tracker updates themselves (density, come-ups, new words) happen in the naturalness-check skill, not here."
---

# Phrasal Verb Tracker: export from the ledger

Since 26.09.26 the phrasal verb tracker lives in the Fluency Ledger database, not in the
.docx. The naturalness check updates it at the end of every session (density against the
native 1-per-192 benchmark, come-up dates, new words). This skill only produces the
.docx on request, exported from the ledger. Murat chose this on 26.09.26: "keep as a file I
can produce on request (exported from the ledger, never edited separately)".

- Dashboard: https://claude.ai/artifact/5ELtvJLvcwMK8EpMW6StvK ("Fluency Ledger"), Phrasal verbs tab.
- Data: `meta/pv_tracker` in that artifact's database: `{as_of, rows: [{word, dates[], notes, list?, practice?}]}`.
  Since 27.09.26 the phrasal verbs from Murat's study list live here too: a row with a `list`
  block (`{ids, exprs, added, importance, mastered}`) is on his list ("list" on the dashboard),
  and `practice: {count, last}` holds its vocab-session reviews. `mastered` is his own label.
- No notes (Murat, 27.09.26: "I don't need any notes from now on"). Old `notes` text stays in the
  data but is never shown, in the export or on the dashboard.
- Never edit the .docx by hand, and never treat it as the source. The ledger is the only home.

## If Murat asks to "update the tracker"

That job belongs to the naturalness check now. Run the `naturalness-check` skill instead (it
measures the chat and updates the tracker in the ledger), then export only if he also asked
for the file.

If this skill was invoked from `mini-prompt-update`'s Step 0 (its old "update the tracker
first" step), check that this chat's session is already in the ledger with phrasal verb data:
`ArtifactData` `get` `sessions/s_<YYYYMMDD>_<first 8 chars of chat id>` and look for a `pv`
block. If it's missing, run `naturalness-check` first. Then hand back to the Mini Prompt
update with the density and come-ups from the session's `pv` block. Don't export the file
unless Murat asks for it.

## Export steps

1. Extract the two scripts at the bottom of this file into `/tmp/pvx`, using the skill's base
   directory (shown when the skill loads):

```bash
mkdir -p /tmp/pvx && cd /tmp/pvx
python3 - "<SKILL_BASE_DIR>/SKILL.md" << 'PYEOF'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
for name, lang, body in re.findall(r"<!-- file: (\S+) -->\s*```(python|javascript)\n(.*?)```", text, re.S):
    open(name, "w", encoding="utf-8").write(body); print("wrote", name)
PYEOF
node -e "require('docx')" 2>/dev/null || npm install -s docx
```

2. `ArtifactData` `get` `meta/pv_tracker` with `out_dir: /tmp/pvx`, then work out the columns
   as of today (stage and recency drift with time alone, so always recalculate against
   today's date):

```bash
cd /tmp/pvx
python3 - << 'PYEOF'
import json
rows = json.load(open('meta/pv_tracker.json'))['rows']
for r in rows:   # study-list status goes in its own column; notes are not shown
    lst, pr = r.get('list'), r.get('practice') or {}
    r['study'] = "" if not lst else "Yes" + (", Mastered" if lst.get('mastered') else "") + (f", {pr['count']} reviews" if pr.get('count') else "")
    r['notes'] = ""
json.dump(rows, open('tracker_in.json', 'w'), ensure_ascii=False)
PYEOF
echo '{"come_ups": [], "new_words": []}' > updates.json
python3 recalc.py tracker_in.json updates.json <DD.MM.YYYY today> tracker_out.json
node render_docx.js tracker_out.json Phrasal_Verb_Activation_Tracker.docx <DD.MM.YYYY today>
```

If `node` can't find `docx` after a global install, run it with `NODE_PATH=$(npm root -g)`.

3. Look at it once before sending: convert to PDF and view the first page image.

```bash
python3 /mnt/skills/public/docx/scripts/office/soffice.py --headless --convert-to pdf Phrasal_Verb_Activation_Tracker.docx
pdftoppm -jpeg -r 80 -f 1 -l 1 Phrasal_Verb_Activation_Tracker.pdf page
```

4. Send the .docx with `SendUserFile`. **Never call `project_write` on this file**: it is a
   binary upload, and `project_write` deletes the existing upload and then fails to create the
   replacement (this once cost real tracker data). If Murat wants the export in the Project
   too, he uploads it himself. Keeping the Project copy current is optional now, because the
   ledger is the source.

5. Report in one or two lines: the date it reflects (recalculated to today), the number of
   words, how many are on his study list, and the count per stage.

## Stage and signal rules (the same as on the ledger page)

- Stage from the number of different days used: 0 Not Yet Observed, 1–2 Emerging, 3–5 In
  Progress, 6+ Activated.
- Recency from days since the last use, against today: up to 7 Green, 8–14 Yellow, 15+ Red.
- Overall Signal is a fixed lookup, never judged:

| Stage \ Recency | Green             | Yellow            | Red                        |
|-----------------|-------------------|-------------------|----------------------------|
| Activated       | Solid & Active    | Solid but Cooling | Fading Despite Strong Base |
| In Progress     | Building Momentum | Stalling          | At Risk                    |
| Emerging        | Fresh Start       | Early Fade        | Lost Spark                 |

## Scripts

<!-- file: recalc.py -->
```python
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
```

<!-- file: render_docx.js -->
```javascript
/**
 * Render the Phrasal Verb Activation Tracker as a styled .docx,
 * matching the existing landscape A4 / dark-blue-header / alternating-row
 * look used for the vocab file in this project.
 *
 * Usage: node render_docx.js <tracker.json> <output.docx> <as_of DD.MM.YYYY>
 *
 * tracker.json rows must already have derived columns populated
 * (word, dates[], study, count, mastery, recency, signal) -- run
 * recalc.py first. This script only lays out and styles; it does not
 * compute anything.
 */
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, ShadingType, PageOrientation, AlignmentType, BorderStyle,
  VerticalAlign, HeadingLevel,
} = require("docx");

const [, , trackerPath, outPath, asOf] = process.argv;
if (!trackerPath || !outPath || !asOf) {
  console.error("Usage: node render_docx.js <tracker.json> <output.docx> <as_of DD.MM.YYYY>");
  process.exit(1);
}

const rows = JSON.parse(fs.readFileSync(trackerPath, "utf8"));

const HEADER_FILL = "1F4E78";
const ALT_FILL = "DCE6F1";
const WHITE_FILL = "FFFFFF";

// Landscape A4: pass portrait dims, docx-js swaps them with the orientation flag.
const PAGE_WIDTH = 11906;  // A4 portrait width (DXA)
const PAGE_HEIGHT = 16838; // A4 portrait height (DXA)
const MARGIN = 720; // 0.5"
const USABLE_WIDTH = PAGE_HEIGHT - 2 * MARGIN; // landscape usable width = portrait height minus margins

// Column widths (DXA), must sum to USABLE_WIDTH
const COLS = [
  { key: "#", label: "#", width: 500 },
  { key: "word", label: "Phrasal Verb", width: 2200 },
  { key: "dates", label: "Come-up Dates", width: 5200 },
  { key: "study", label: "My Study List", width: 2400 },
  { key: "count", label: "Come-up Count", width: 1100 },
  { key: "mastery", label: "Mastery Status", width: 1600 },
  { key: "recency", label: "Recency Status", width: 1400 },
  { key: "signal", label: "Overall Signal", width: 2000 },
];
const colSum = COLS.reduce((s, c) => s + c.width, 0);
const scale = USABLE_WIDTH / colSum;
COLS.forEach((c) => (c.width = Math.round(c.width * scale)));

function cell(text, { fill, bold = false, color = "000000", width, align = AlignmentType.LEFT }) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill, color: "auto" },
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
    children: [
      new Paragraph({
        alignment: align,
        children: [new TextRun({ text: String(text ?? ""), bold, color })],
      }),
    ],
  });
}

const headerRow = new TableRow({
  tableHeader: true,
  children: COLS.map((c) =>
    cell(c.label, { fill: HEADER_FILL, bold: true, color: "FFFFFF", width: c.width, align: AlignmentType.CENTER })
  ),
});

const dataRows = rows.map((r, i) => {
  const fill = i % 2 === 0 ? WHITE_FILL : ALT_FILL;
  const values = {
    "#": i + 1,
    word: r.word,
    dates: (r.dates || []).join(", "),
    study: r.study || "",
    count: r.count,
    mastery: r.mastery,
    recency: r.recency || "",
    signal: r.signal,
  };
  return new TableRow({
    children: COLS.map((c) =>
      cell(values[c.key], {
        fill,
        width: c.width,
        align: ["#", "count", "mastery", "recency", "signal"].includes(c.key)
          ? AlignmentType.CENTER
          : AlignmentType.LEFT,
      })
    ),
  });
});

const table = new Table({
  width: { size: USABLE_WIDTH, type: WidthType.DXA },
  columnWidths: COLS.map((c) => c.width),
  rows: [headerRow, ...dataRows],
  borders: {
    top: { style: BorderStyle.SINGLE, size: 2, color: "AAAAAA" },
    bottom: { style: BorderStyle.SINGLE, size: 2, color: "AAAAAA" },
    left: { style: BorderStyle.SINGLE, size: 2, color: "AAAAAA" },
    right: { style: BorderStyle.SINGLE, size: 2, color: "AAAAAA" },
    insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: "AAAAAA" },
    insideVertical: { style: BorderStyle.SINGLE, size: 2, color: "AAAAAA" },
  },
});

const doc = new Document({
  sections: [
    {
      properties: {
        page: {
          size: { width: PAGE_WIDTH, height: PAGE_HEIGHT, orientation: PageOrientation.LANDSCAPE },
          margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN },
        },
      },
      children: [
        new Paragraph({
          heading: HeadingLevel.HEADING_1,
          children: [new TextRun({ text: "Phrasal Verb Activation Tracker", bold: true })],
        }),
        new Paragraph({
          children: [
            new TextRun({
              text: `Last updated: ${asOf} | ${rows.length} phrasal verbs tracked (vocab file + spontaneous additions) | Sorted by Come-up Count (descending)`,
              italics: true,
              size: 20,
            }),
          ],
        }),
        new Paragraph({ text: "" }),
        table,
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(outPath, buf);
  console.log(`Wrote ${outPath} (${rows.length} rows)`);
});
```