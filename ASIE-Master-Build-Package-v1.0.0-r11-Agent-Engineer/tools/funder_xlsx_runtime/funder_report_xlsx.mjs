import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const inputPath = process.argv[2];
const outputPath = process.argv[3];
if (!inputPath || !outputPath) throw new Error("usage: funder_report_xlsx.mjs projection.json output.xlsx");

const projection = JSON.parse(await fs.readFile(inputPath, "utf8"));
const workbook = Workbook.create();
const cover = workbook.worksheets.add("Cover");
const financials = workbook.worksheets.add("Financials");
const sections = workbook.worksheets.add("Sections");
const evidence = workbook.worksheets.add("Evidence");

const navy = "#172554";
const blue = "#2563EB";
const light = "#EFF6FF";
const line = "#CBD5E1";
const money = "#,##0;[Red](#,##0);-";

function title(sheet, range, text) {
  sheet.getRange(range).merge();
  sheet.getRange(range).values = [[text]];
  sheet.getRange(range).format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 16 }, horizontalAlignment: "right", verticalAlignment: "center" };
  sheet.getRange(range).format.rowHeight = 30;
}
function header(range) {
  range.format = { fill: blue, font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "right", wrapText: true, borders: { preset: "all", style: "thin", color: line } };
}
function body(range) {
  range.format = { font: { color: "#0F172A" }, horizontalAlignment: "right", wrapText: true, borders: { preset: "all", style: "thin", color: line } };
}

cover.showGridLines = false;
title(cover, "A1:F1", "ASIE - Funder-Ready Report Pack");
cover.getRange("A3:B8").values = [
  ["Contract", projection.contract_id || ""],
  ["Profile", projection.profile_id || ""],
  ["Readiness", projection.readiness_status || ""],
  ["Snapshot ID", projection.snapshot_id || ""],
  ["Run ID", projection.run_id || ""],
  ["Projection hash", projection.projection_hash || ""],
];
cover.getRange("A9:B9").values = [["Profile readiness", (projection.profile_readiness || {}).status || ""]];
cover.getRange("A3:A9").format = { fill: light, font: { bold: true, color: navy }, horizontalAlignment: "right" };
cover.getRange("B3:B9").format = { font: { color: "#0F172A" }, horizontalAlignment: "right", wrapText: true };
cover.getRange("A10:F12").merge();
cover.getRange("A10:F12").values = [["This workbook is a read-only projection of an immutable ASIE Snapshot. It does not recalculate or guarantee funding acceptance."]];
cover.getRange("A10:F12").format = { fill: "#FFF7ED", font: { color: "#7C2D12", italic: true }, wrapText: true, verticalAlignment: "center", horizontalAlignment: "right" };
cover.getRange("A:A").format.columnWidth = 22;
cover.getRange("B:B").format.columnWidth = 38;
cover.getRange("C:F").format.columnWidth = 14;

financials.showGridLines = false;
title(financials, "A1:G1", "Financial Projection (Snapshot-linked)");
financials.getRange("A3:G3").values = [["Year", "Revenue", "Gross profit", "EBITDA", "EBIT", "Operating cashflow", "Status"]];
header(financials.getRange("A3:G3"));
const section14 = (projection.sections || []).find((row) => row.section_id === "14-financial-expectations") || {};
const years = (((section14.payload || {}).statements || {}).income_statement || {}).years || [];
financials.getRange(`A4:G${3 + Math.max(years.length, 1)}`).values = (years.length ? years : [{ year: "-", revenue: null, gross_profit: null, ebitda: null, ebit: null, net_operating_cashflow: null }]).map((row) => [row.year, row.revenue, row.gross_profit, row.ebitda, row.ebit, row.net_operating_cashflow, "projected"]);
body(financials.getRange(`A4:G${3 + Math.max(years.length, 1)}`));
financials.getRange(`B4:F${3 + Math.max(years.length, 1)}`).format.numberFormat = money;
const totalRow = 5 + years.length;
financials.getRange(`A${totalRow}:G${totalRow}`).values = [["Total / check", null, null, null, null, null, "formula"]];
financials.getRange(`B${totalRow}:F${totalRow}`).formulas = [[`=SUM(B4:B${3 + Math.max(years.length, 1)})`, `=SUM(C4:C${3 + Math.max(years.length, 1)})`, `=SUM(D4:D${3 + Math.max(years.length, 1)})`, `=SUM(E4:E${3 + Math.max(years.length, 1)})`, `=SUM(F4:F${3 + Math.max(years.length, 1)})`]];
financials.getRange(`A${totalRow}:G${totalRow}`).format = { fill: light, font: { bold: true }, borders: { top: { style: "medium", color: navy }, bottom: { style: "thin", color: line } } };
financials.getRange("A:A").format.columnWidth = 14;
financials.getRange("B:F").format.columnWidth = 17;
financials.getRange("G:G").format.columnWidth = 16;
financials.freezePanes.freezeRows(3);

sections.showGridLines = false;
title(sections, "A1:D1", "Study Sections 1-16");
sections.getRange("A3:D3").values = [["Section", "Title", "Status", "Source refs"]];
header(sections.getRange("A3:D3"));
const sectionRows = (projection.sections || []).map((row) => [row.section_id || "", row.title || "", row.status || "", (row.source_refs || []).join(", ")]);
sections.getRange(`A4:D${3 + Math.max(sectionRows.length, 1)}`).values = sectionRows.length ? sectionRows : [["-", "No sections", "not_ready", ""]];
body(sections.getRange(`A4:D${3 + Math.max(sectionRows.length, 1)}`));
sections.getRange("A:A").format.columnWidth = 24;
sections.getRange("B:B").format.columnWidth = 34;
sections.getRange("C:C").format.columnWidth = 18;
sections.getRange("D:D").format.columnWidth = 38;
sections.freezePanes.freezeRows(3);

evidence.showGridLines = false;
title(evidence, "A1:C1", "Evidence and Assumption Traceability");
evidence.getRange("A3:C3").values = [["Evidence register", "Assumption refs", "Lineage entries"]];
header(evidence.getRange("A3:C3"));
const ev = projection.evidence || {};
evidence.getRange("A4:C4").values = [[ev.evidence_register_id || "", (ev.assumption_refs || []).join(", "), (ev.transformation_lineage || []).length]];
body(evidence.getRange("A4:C4"));
evidence.getRange("A:A").format.columnWidth = 28;
evidence.getRange("B:B").format.columnWidth = 52;
evidence.getRange("C:C").format.columnWidth = 18;

await fs.mkdir(new URL(".", `file://${outputPath.replaceAll("\\", "/")}`).pathname).catch(() => {});
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
const qaDir = outputPath.replace(/\\[^\\]+$/, "\\qa");
await fs.mkdir(qaDir, { recursive: true });
for (const sheetName of ["Cover", "Financials", "Sections", "Evidence"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(`${qaDir}\\${sheetName}.png`, new Uint8Array(await preview.arrayBuffer()));
}
