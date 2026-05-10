import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const spreadsheetId = process.env.GOOGLE_SHEET_ID || "1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E";
const sheetName = process.env.GOOGLE_SHEET_NAME || "dges_cursos_2026";
const range = process.env.GOOGLE_SHEET_RANGE || `${sheetName}!A1:AD2000`;
const account = process.env.GOG_ACCOUNT || "tiago.carvalho@gmail.com";
const outputPath = path.join(process.cwd(), "data", "courses.csv");

function csvEscape(value) {
  const text = String(value ?? "");
  if (/[",\n\r]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
  return text;
}

const { stdout } = await execFileAsync("gog", [
  "sheets",
  "get",
  spreadsheetId,
  range,
  "--account",
  account,
  "--json",
  "--no-input"
], { maxBuffer: 20 * 1024 * 1024 });

const payload = JSON.parse(stdout);
const values = payload.values;
if (!Array.isArray(values) || values.length < 2) {
  throw new Error("No spreadsheet rows returned by gog.");
}

const width = Math.max(...values.map((row) => row.length));
const csv = values
  .map((row) => Array.from({ length: width }, (_, index) => csvEscape(row[index] ?? "")).join(","))
  .join("\n") + "\n";

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.writeFile(outputPath, csv);
console.log(`Wrote ${values.length - 1} rows to ${outputPath}`);
