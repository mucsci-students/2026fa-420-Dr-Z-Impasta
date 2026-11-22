/**
 * Draws a schedule PDF from the description built in schedulePdf.js, with jsPDF and
 * jspdf-autotable. This is the only file that imports them, and the viewer loads it on
 * the first export, so the libraries are not part of the page's first download.
 *
 * Layout, chosen for printing rather than to match the on-screen timetable:
 * - US Letter or A4, portrait, 0.75 in margins, Helvetica 10 pt (9.5 pt in tables).
 * - Black text, gray rules and a light gray header row, so it reads the same in grayscale.
 * - One bold heading and one table per room, lab, or faculty member. A heading is never
 *   left alone at the bottom of a page; a table that continues repeats its column
 *   headings and names the section again; a row is never split across pages.
 * - Columns always fit the page width; long course and faculty names wrap.
 * - "Page 1 of 3" and the schedule's name at the bottom of every page.
 *
 * Text is drawn with the PDF's built-in Helvetica, which covers Western European
 * characters. Other characters are written in their closest plain form (see pdfText).
 */
import { jsPDF } from "jspdf";
import { autoTable } from "jspdf-autotable";

const MARGIN = 54; // 0.75 in, in points
const CONTINUED_SPACE = 20; // room above a continued table for the section's name
const BLACK = 0;
const RULE_GRAY = 110;
const HEAD_GRAY = 228;
const MUTED_GRAY = 70;

/** Typographic characters the built-in font lacks, as [pattern, plain replacement]. */
const PLAIN_PUNCTUATION = [
  [/[\u2010-\u2015]/g, "-"], // hyphens and dashes
  [/[\u2018\u2019]/g, "'"], // curly single quotes
  [/[\u201c\u201d]/g, '"'], // curly double quotes
  [/\u2026/g, "..."], // ellipsis
  [/\u00a0/g, " "], // no-break space
];

/**
 * Text the built-in font can draw. Typographic dashes and quotes become plain ones, and
 * a letter outside Latin-1 loses its accent (a Vietnamese "e" with two marks becomes
 * "e") or, failing that, becomes "?".
 */
export function pdfText(value) {
  let text = String(value ?? "");
  for (const [pattern, plain] of PLAIN_PUNCTUATION) text = text.replace(pattern, plain);
  return text.replace(/[^\t\n\r -\u00ff]/g, (char) => {
    const unaccented = char.normalize("NFKD").replace(/\p{M}/gu, "");
    return /^[ -\u00ff]+$/.test(unaccented) ? unaccented : "?";
  });
}

/** "November 13, 2026 at 10:13 AM", the same on every machine. */
function formatGenerated(date) {
  return (
    date.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) +
    " at " +
    date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
  );
}

/**
 * Draw `pdf` (from buildSchedulePdf) and return the jsPDF document. `now` is printed as
 * the "Generated" time.
 */
export function drawSchedulePdf(pdf, { now = new Date() } = {}) {
  const doc = new jsPDF({ unit: "pt", format: pdf.paper, orientation: "portrait" });
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const contentWidth = pageWidth - MARGIN * 2;
  const bottom = pageHeight - MARGIN;
  doc.setProperties({ title: pdfText(`${pdf.title}: ${pdf.subtitle}`), creator: "Dr. ZImpasta" });
  doc.setTextColor(BLACK);

  // ---- Header: what this document is, on the first page.
  let y = MARGIN + 6;
  doc.setFont("helvetica", "bold").setFontSize(16);
  doc.text(pdfText(pdf.title).toUpperCase(), MARGIN, y);
  y += 20;
  doc.setFontSize(12);
  for (const line of doc.splitTextToSize(pdfText(pdf.subtitle), contentWidth)) {
    doc.text(line, MARGIN, y);
    y += 15;
  }
  y += 5;
  doc.setFontSize(10);
  const details = [...pdf.details, ["Generated", formatGenerated(now)]];
  const labelWidth =
    Math.max(...details.map(([label]) => doc.getTextWidth(`${pdfText(label)}:`))) + 8;
  for (const [label, value] of details) {
    doc.setFont("helvetica", "bold");
    doc.text(`${pdfText(label)}:`, MARGIN, y);
    doc.setFont("helvetica", "normal");
    const lines = doc.splitTextToSize(pdfText(value), contentWidth - labelWidth);
    doc.text(lines, MARGIN + labelWidth, y);
    y += 14 * lines.length;
  }
  y += 2;
  doc.setDrawColor(RULE_GRAY).setLineWidth(1);
  doc.line(MARGIN, y, pageWidth - MARGIN, y);
  y += 22;

  // ---- One heading and table per room, lab, or faculty member.
  for (const section of pdf.sections) {
    doc.setFont("helvetica", "bold").setFontSize(12);
    const headingLines = doc.splitTextToSize(pdfText(section.heading), contentWidth);
    // Keep the heading with its column headings and at least two rows.
    const needed = headingLines.length * 15 + 14 + 3 * 22;
    if (y + needed > bottom) {
      doc.addPage();
      y = MARGIN + 10;
    }
    doc.setTextColor(BLACK);
    doc.text(headingLines, MARGIN, y);
    y += headingLines.length * 15 - 2;
    doc.setFont("helvetica", "normal").setFontSize(9).setTextColor(MUTED_GRAY);
    doc.text(pdfText(section.summary), MARGIN, y);
    doc.setTextColor(BLACK);
    y += 8;

    const continued = pdfText(`${section.heading} (continued)`);
    autoTable(doc, {
      startY: y,
      margin: { top: MARGIN + CONTINUED_SPACE, right: MARGIN, bottom: MARGIN + 14, left: MARGIN },
      tableWidth: contentWidth,
      theme: "grid",
      showHead: "everyPage",
      rowPageBreak: "avoid",
      head: [pdf.columns.map(pdfText)],
      body: section.rows.map((row) =>
        [row.course, row.section, row.type, row.other, row.days, row.start, row.end].map(pdfText),
      ),
      styles: {
        font: "helvetica",
        fontSize: 9.5,
        cellPadding: { top: 4, right: 5, bottom: 4, left: 5 },
        textColor: BLACK,
        lineColor: RULE_GRAY,
        lineWidth: 0.5,
        overflow: "linebreak",
        valign: "top",
      },
      headStyles: { fillColor: HEAD_GRAY, textColor: BLACK, fontStyle: "bold" },
      // Short, fixed columns keep their width; course and faculty or room share the rest
      // and wrap when a name is long, so no column is ever cut off.
      columnStyles: {
        0: { cellWidth: 90 },
        1: { cellWidth: 48 },
        2: { cellWidth: 100 },
        3: { cellWidth: "auto" },
        4: { cellWidth: 44 },
        5: { cellWidth: 56 },
        6: { cellWidth: 56 },
      },
      didDrawPage(data) {
        if (data.pageNumber === 1) return; // The heading is already above the table.
        doc.setFont("helvetica", "bold").setFontSize(10).setTextColor(BLACK);
        doc.text(doc.splitTextToSize(continued, contentWidth)[0], MARGIN, MARGIN + 10);
      },
    });
    y = doc.lastAutoTable.finalY + 26;
  }

  // ---- Notes, when the tables need explaining.
  if (pdf.notes.length) {
    doc.setFont("helvetica", "normal").setFontSize(9);
    for (const note of pdf.notes) {
      const lines = doc.splitTextToSize(pdfText(note), contentWidth);
      if (y + lines.length * 12 > bottom - 14) {
        doc.addPage();
        y = MARGIN + 10;
      }
      doc.text(lines, MARGIN, y);
      y += lines.length * 12 + 4;
    }
  }

  // ---- Footer on every page, once the page count is known.
  const pages = doc.getNumberOfPages();
  const footer = pdfText(pdf.footer);
  for (let page = 1; page <= pages; page += 1) {
    doc.setPage(page);
    doc.setFont("helvetica", "normal").setFontSize(9).setTextColor(MUTED_GRAY);
    const pageText = `Page ${page} of ${pages}`;
    const room = contentWidth - doc.getTextWidth(pageText) - 16;
    doc.text(doc.splitTextToSize(footer, room)[0], MARGIN, pageHeight - 30);
    doc.text(pageText, pageWidth - MARGIN, pageHeight - 30, { align: "right" });
  }
  return doc;
}

/** The finished file: `{ filename, content }` with `content` the PDF's bytes. */
export function createSchedulePdfFile(pdf, options) {
  return { filename: pdf.filename, content: drawSchedulePdf(pdf, options).output("arraybuffer") };
}
