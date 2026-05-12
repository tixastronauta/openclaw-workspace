import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

// Minimal CSV parser — handles quoted fields with commas/newlines
function parseCsv(text) {
  const rows = [];
  let headers = null;
  let field = "";
  let inQuotes = false;
  let currentRow = [];

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const next = text[i + 1];

    if (inQuotes) {
      if (ch === '"' && next === '"') {
        field += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        field += ch;
      }
    } else {
      if (ch === '"') {
        inQuotes = true;
      } else if (ch === ",") {
        currentRow.push(field);
        field = "";
      } else if (ch === "\n" || (ch === "\r" && next === "\n")) {
        if (ch === "\r") i++;
        currentRow.push(field);
        field = "";
        if (headers === null) {
          headers = currentRow;
        } else if (currentRow.some((f) => f !== "")) {
          const obj = {};
          for (let j = 0; j < headers.length; j++) {
            obj[headers[j]] = currentRow[j] ?? "";
          }
          rows.push(obj);
        }
        currentRow = [];
      } else {
        field += ch;
      }
    }
  }

  // Last row (no trailing newline)
  if (field !== "" || currentRow.length > 0) {
    currentRow.push(field);
    if (headers && currentRow.some((f) => f !== "")) {
      const obj = {};
      for (let j = 0; j < headers.length; j++) {
        obj[headers[j]] = currentRow[j] ?? "";
      }
      rows.push(obj);
    }
  }

  return rows;
}

function slugify(str) {
  return str
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

const csvPath = path.join(root, "data", "courses.csv");
const outPath = path.join(root, "public", "search-index.json");

const csv = fs.readFileSync(csvPath, "utf8");
const rows = parseCsv(csv);

const seen = new Map();
const entries = [];

// Mirror the slug logic from lib/courses.ts: courseName + institutionName + courseCode + institutionCode
for (const row of rows) {
  const courseName = row["course_name"]?.trim();
  const institutionName = row["institution_name"]?.trim();
  const institutionSigla = row["institution_sigla"]?.trim();
  const institutionCode = row["institution_code"]?.trim();
  const courseCode = row["course_code"]?.trim();

  if (!courseName) continue;

  const parts = [courseName, institutionName, courseCode, institutionCode].filter(Boolean).join(" ");
  const baseSlug = slugify(parts);
  const count = seen.get(baseSlug) ?? 0;
  seen.set(baseSlug, count + 1);
  const slug = count === 0 ? baseSlug : `${baseSlug}-${count + 1}`;

  entries.push({
    slug,
    n: courseName,
    ...(institutionName ? { i: institutionName } : {}),
    ...(institutionSigla ? { s: institutionSigla } : {}),
    ...(institutionCode ? { ic: institutionCode } : {}),
  });
}

// Sort same as getAllCourses: by courseName, then institutionName
entries.sort((a, b) => a.n.localeCompare(b.n, "pt") || (a.i ?? "").localeCompare(b.i ?? "", "pt"));

fs.writeFileSync(outPath, JSON.stringify(entries));
console.log(`search-index.json: ${entries.length} entries, ${(fs.statSync(outPath).size / 1024).toFixed(1)} KB`);
