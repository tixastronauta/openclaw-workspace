#!/usr/bin/env node
import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

const spreadsheetId = process.env.GOOGLE_SHEET_ID || "1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E";
const sheetName = process.env.GOOGLE_SHEET_NAME || "dges_cursos_2026";
const range = process.env.GOOGLE_SHEET_RANGE || `${sheetName}!A1:ZZ2000`;
const account = process.env.GOG_ACCOUNT || "tiago.carvalho@gmail.com";
const outputPath = path.join(root, "data", "courses.csv");
const searchIndexScript = path.join(root, "scripts", "generate-search-index.mjs");

const requiredHeaders = [
  "course_code",
  "course_name",
  "course_description",
  "cycle",
  "institution_code",
  "institution_name",
  "reference"
];

function csvEscape(value) {
  const text = String(value ?? "");
  if (/[",\n\r]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
  return text;
}

function trimTrailingEmptyCells(row) {
  const next = [...row];
  while (next.length > 0 && String(next.at(-1) ?? "").trim() === "") next.pop();
  return next;
}

function normaliseRows(values) {
  const trimmedRows = values
    .map(trimTrailingEmptyCells)
    .filter((row) => row.some((value) => String(value ?? "").trim() !== ""));

  if (trimmedRows.length < 2) {
    throw new Error("No spreadsheet data rows returned by gog.");
  }

  const width = Math.max(...trimmedRows.map((row) => row.length));
  return trimmedRows.map((row) => Array.from({ length: width }, (_, index) => row[index] ?? ""));
}

function validateHeaders(headers) {
  const missing = requiredHeaders.filter((header) => !headers.includes(header));
  if (missing.length > 0) {
    throw new Error(`Spreadsheet is missing required columns: ${missing.join(", ")}`);
  }
}

function countFilledDescriptions(rows, headers) {
  const descriptionIndex = headers.indexOf("course_description");
  return rows.slice(1).filter((row) => String(row[descriptionIndex] ?? "").trim() !== "").length;
}

async function gogGetSheet() {
  const { stdout } = await execFileAsync("gog", [
    "sheets",
    "get",
    spreadsheetId,
    range,
    "--account",
    account,
    "--json",
    "--no-input"
  ], { maxBuffer: 50 * 1024 * 1024 });

  const payload = JSON.parse(stdout);
  if (!Array.isArray(payload.values)) {
    throw new Error("Unexpected gog response: missing values array.");
  }
  return payload.values;
}

async function main() {
  console.log(`Syncing ${sheetName} from Google Sheets...`);
  const values = normaliseRows(await gogGetSheet());
  const headers = values[0].map((value) => String(value ?? "").trim());
  validateHeaders(headers);

  const csv = values
    .map((row) => row.map(csvEscape).join(","))
    .join("\n") + "\n";

  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, csv, "utf8");

  const dataRows = values.length - 1;
  const filledDescriptions = countFilledDescriptions(values, headers);
  console.log(`Wrote ${dataRows} rows to ${path.relative(root, outputPath)}`);
  console.log(`course_description filled: ${filledDescriptions}/${dataRows}`);

  console.log("Regenerating search index...");
  await execFileAsync(process.execPath, [searchIndexScript], { cwd: root, maxBuffer: 20 * 1024 * 1024 });
  console.log("Done.");
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
