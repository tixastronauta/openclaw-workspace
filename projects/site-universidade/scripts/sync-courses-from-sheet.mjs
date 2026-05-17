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

function parseCsvLine(line) {
  const cells = [];
  let cell = "";
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];

    if (char === '"' && inQuotes && next === '"') {
      cell += '"';
      index += 1;
      continue;
    }

    if (char === '"') {
      inQuotes = !inQuotes;
      continue;
    }

    if (char === "," && !inQuotes) {
      cells.push(cell);
      cell = "";
      continue;
    }

    cell += char;
  }

  cells.push(cell);
  return cells;
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
  const duplicateHeaders = headers.filter((header, index) => headers.indexOf(header) !== index);
  if (duplicateHeaders.length > 0) {
    throw new Error(`Spreadsheet has duplicate columns: ${[...new Set(duplicateHeaders)].join(", ")}`);
  }

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

async function getCurrentCsvHeaders() {
  try {
    const csv = await fs.readFile(outputPath, "utf8");
    const [headerLine] = csv.split(/\r?\n/, 1);
    const headers = parseCsvLine(headerLine).map((header) => header.trim()).filter(Boolean);
    if (headers.length > 0) return headers;
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }

  return null;
}

function buildOutputHeaders(sheetHeaders, currentCsvHeaders) {
  if (!currentCsvHeaders) return sheetHeaders;

  const missingCurrentHeaders = currentCsvHeaders.filter((header) => !sheetHeaders.includes(header));
  if (missingCurrentHeaders.length > 0) {
    throw new Error(
      `Spreadsheet is missing columns that already exist in data/courses.csv: ${missingCurrentHeaders.join(", ")}`
    );
  }

  const newSheetHeaders = sheetHeaders.filter((header) => !currentCsvHeaders.includes(header));
  return [...currentCsvHeaders, ...newSheetHeaders];
}

function reorderRowsByHeader(values, outputHeaders) {
  const sheetHeaders = values[0].map((value) => String(value ?? "").trim());
  const sheetIndexes = new Map(sheetHeaders.map((header, index) => [header, index]));
  return [
    outputHeaders,
    ...values.slice(1).map((row) => outputHeaders.map((header) => row[sheetIndexes.get(header)] ?? ""))
  ];
}

export async function main() {
  console.log(`Syncing ${sheetName} from Google Sheets...`);
  const values = normaliseRows(await gogGetSheet());
  const headers = values[0].map((value) => String(value ?? "").trim());
  validateHeaders(headers);
  const currentCsvHeaders = await getCurrentCsvHeaders();
  const outputHeaders = buildOutputHeaders(headers, currentCsvHeaders);
  const outputValues = reorderRowsByHeader(values, outputHeaders);

  const csv = outputValues
    .map((row) => row.map(csvEscape).join(","))
    .join("\n") + "\n";

  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, csv, "utf8");

  const dataRows = outputValues.length - 1;
  const filledDescriptions = countFilledDescriptions(outputValues, outputHeaders);
  const addedColumns = outputHeaders.filter((header) => !currentCsvHeaders?.includes(header));
  console.log(`Wrote ${dataRows} rows to ${path.relative(root, outputPath)}`);
  console.log(`CSV columns: ${outputHeaders.length} (${addedColumns.length} new from sheet)`);
  if (addedColumns.length > 0) console.log(`Added columns: ${addedColumns.join(", ")}`);
  console.log(`course_description filled: ${filledDescriptions}/${dataRows}`);

  console.log("Regenerating search index...");
  await execFileAsync(process.execPath, [searchIndexScript], { cwd: root, maxBuffer: 20 * 1024 * 1024 });
  console.log("Done.");
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  });
}
