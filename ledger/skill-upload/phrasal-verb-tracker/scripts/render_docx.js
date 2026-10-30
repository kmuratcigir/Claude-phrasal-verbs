/**
 * Render the Phrasal Verb Activation Tracker as a styled .docx,
 * matching the existing landscape A4 / dark-blue-header / alternating-row
 * look used for the vocab file in this project.
 *
 * Usage: node render_docx.js <tracker.json> <output.docx> <as_of DD.MM.YYYY>
 *
 * tracker.json rows must already have derived columns populated
 * (word, dates[], notes, count, mastery, recency, signal) -- run
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
  { key: "notes", label: "Notes", width: 5200 },
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
    notes: r.notes || "",
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
