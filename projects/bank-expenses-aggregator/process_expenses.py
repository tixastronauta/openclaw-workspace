#!/usr/bin/env python3
"""Process bank account CSVs and credit-card statement PDFs into the expenses Sheet.

The script discovers source files from a Google Drive folder, parses all known bank
formats, applies categorisation rules from the spreadsheet, and overwrites the
`Movimentos` tab with the consolidated result.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import tempfile
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

DEFAULT_FOLDER_ID = "1ngT8XwYJ6L9FpYpO4XZ0Bg8nX9Ur4xq1"
DEFAULT_SPREADSHEET_ID = "1OqVVZPawOU_8bakipfUVSrofmiJeJTiAbkZLtaDE20Y"
DEFAULT_ACCOUNT = "tiago.carvalho@gmail.com"
TARGET_TITLE = "Movimentos Bancários"

MOV_HEADERS = ["Banco", "Tipo", "Mes", "Data", "Descritivo", "Valor", "Categoria", "Fonte"]
RULES_RANGE = "'Regras Catalogacao'!A1:I500"
CATEGORIES_RANGE = "Categorias!A1:A500"


@dataclass(frozen=True)
class DriveFile:
    id: str
    name: str
    mime_type: str


@dataclass
class Expense:
    bank: str
    kind: str
    statement_month: str
    tx_date: date
    description: str
    value: float
    source: str
    category: str = ""


@dataclass(frozen=True)
class Rule:
    row: int
    active: bool
    priority: int
    text: str
    value: float | None
    match_type: str
    bank: str
    kind: str
    category: str
    notes: str


def run(cmd: list[str], *, capture: bool = True, cwd: Path | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=capture)
    return result.stdout if capture else ""


def gog(args: list[str], account: str, *, capture: bool = True, cwd: Path | None = None) -> str:
    return run(["gog", *args, "--no-input", "-a", account], capture=capture, cwd=cwd)


def norm(text: Any) -> str:
    value = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", value.lower()).strip()


def amount(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace("\ufeff", "").replace("€", "")
    if not s:
        return None
    sign = -1 if s.startswith("-") else 1
    s = s.lstrip("+-").strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return round(sign * float(s), 2)


def parse_date(value: str) -> date:
    value = value.strip()
    # Some bank CSV exports occasionally mix normal dates with Excel/Sheets
    # serial dates (for example 46111). Treat those as Google/Excel serials.
    if re.fullmatch(r"\d{5}(?:\.0)?", value):
        return date(1899, 12, 30) + timedelta(days=int(float(value)))
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unsupported date: {value!r}")


def google_serial(d: date) -> int:
    return (d - date(1899, 12, 30)).days


def parse_source_name(name: str) -> tuple[str, str, str] | None:
    """Return (bank, source_type, YYYY-MM) for known filenames."""
    m = re.match(r"^(?P<bank>[^-]+)-(?P<label>ExtratoCartao|Movimentos)-(?P<ym>\d{6})\.(?P<ext>pdf|csv)$", name, re.I)
    if not m:
        return None
    bank = m.group("bank")
    ym = m.group("ym")
    label = m.group("label")
    source_type = "card_pdf" if label.lower() == "extratocartao" else "account_csv"
    return bank, source_type, f"{ym[:4]}-{ym[4:6]}"


def list_folder(folder_id: str, account: str) -> list[DriveFile]:
    raw = gog(["drive", "ls", "--parent", folder_id, "--max", "500", "--json"], account)
    data = json.loads(raw)
    return [DriveFile(id=f["id"], name=f["name"], mime_type=f["mimeType"]) for f in data.get("files", [])]


def download(file: DriveFile, dest: Path, account: str) -> None:
    gog(["drive", "download", file.id, "--out", str(dest)], account, capture=True)


def pdf_to_text(pdf_path: Path) -> str:
    txt_path = pdf_path.with_suffix(".txt")
    run(["pdftotext", "-layout", str(pdf_path), str(txt_path)])
    return txt_path.read_text(encoding="utf-8", errors="replace")


def add_expense(rows: list[Expense], *, bank: str, kind: str, statement_month: str, tx_date: date, description: str, value: float | None, source: str) -> None:
    if value is None or value <= 0:
        return
    rows.append(Expense(bank=bank, kind=kind, statement_month=statement_month, tx_date=tx_date, description=" ".join(description.split()), value=round(value, 2), source=source))


# ---- Credit-card PDF parsers -------------------------------------------------

def parse_activo_card(text: str, statement_month: str, source: str) -> list[Expense]:
    rows: list[Expense] = []
    capture = False
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if not capture:
            capture = line == "DETALHE DOS MOVIMENTOS"
            continue
        m = re.match(r"^(\d{4})/(\d{2})/(\d{2})\s+(\d{4})/(\d{2})/(\d{2})\s+(.+?)\s+([0-9]+(?:[.,][0-9]{2}))$", line)
        if not m:
            continue
        y, mo, d, _yv, _mv, _dv, desc, val = m.groups()
        if desc.strip().startswith(">") or "PAGAMENTO CARTAO" in desc.upper():
            continue
        add_expense(rows, bank="ActivoBank", kind="Cartão", statement_month=statement_month, tx_date=date(int(y), int(mo), int(d)), description=desc, value=amount(val), source=source)
    return rows


def parse_cgd_card(text: str, statement_month: str, source: str) -> list[Expense]:
    rows: list[Expense] = []
    for raw in text.splitlines():
        line = " ".join(raw.split())
        m = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(.+?)\s+([0-9]+,[0-9]{2})\s+([0-9]+,[0-9]{2})$", line)
        if not m:
            continue
        tx_date, desc, debit, _credit = m.groups()
        desc = desc.strip()
        if desc.startswith("Saldo Cred") or desc.startswith("Extrato") or "PAGAMENTO AUTOMATICO" in desc.upper():
            continue
        add_expense(rows, bank="CGD", kind="Cartão", statement_month=statement_month, tx_date=parse_date(tx_date), description=desc, value=amount(debit), source=source)
    return rows


def parse_unibanco_card(text: str, statement_month: str, source: str) -> list[Expense]:
    rows: list[Expense] = []
    period = re.search(r"Periodo de Extrato:\s*(\d{4})-\d{2}-\d{2}\s+a\s+(\d{4})-\d{2}-\d{2}", text)
    year = int(period.group(1)) if period else int(statement_month[:4])
    for raw in text.splitlines():
        line = " ".join(raw.split())
        m = re.match(r"^(\d{2})\.(\d{2})\s+\d{2}\.\d{2}\s+(.+?)\s+([0-9]+,[0-9]{2})EUR\s+([0-9]+,[0-9]{2})$", line)
        if not m:
            continue
        d, mo, desc, _original, debit = m.groups()
        add_expense(rows, bank="Unibanco", kind="Cartão", statement_month=statement_month, tx_date=date(year, int(mo), int(d)), description=desc, value=amount(debit), source=source)
    return rows


def parse_universo_card(text: str, statement_month: str, source: str) -> list[Expense]:
    rows: list[Expense] = []
    period = re.search(r"Movimentos de:\s*(\d{2})/(\d{2})/(\d{4})\s+a\s+(\d{2})/(\d{2})/(\d{4})", text)
    start_year = end_year = int(statement_month[:4])
    start_month = int(statement_month[5:7])
    if period:
        _sd, sm, sy, _ed, _em, ey = period.groups()
        start_year, end_year, start_month = int(sy), int(ey), int(sm)
    for raw in text.splitlines():
        line = " ".join(raw.split())
        m = re.match(r"^(\d{2})/(\d{2})\s+\d{2}/\d{2}\s+(.+?)\s+([0-9]+,[0-9]{2})\s+€\s+(-?[0-9]+,[0-9]{2})\s+€$", line)
        if not m:
            continue
        d, mo, desc, _fee, total = m.groups()
        desc = desc.strip()
        if desc.lower().startswith("saldo") or "debito banco" in desc.lower():
            continue
        total_value = amount(total)
        if total_value is None or total_value >= 0:
            continue
        year = start_year if int(mo) >= start_month else end_year
        add_expense(rows, bank="Universo", kind="Cartão", statement_month=statement_month, tx_date=date(year, int(mo), int(d)), description=desc, value=abs(total_value), source=source)
    return rows


CARD_PARSERS = {
    "activobank": parse_activo_card,
    "cgd": parse_cgd_card,
    "unibanco": parse_unibanco_card,
    "universo": parse_universo_card,
}


# ---- Account CSV parsers ------------------------------------------------------

def parse_activobank_account(path: Path, statement_month: str, source: str) -> list[Expense]:
    rows: list[Expense] = []
    all_rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))
    start = next(i for i, r in enumerate(all_rows) if r and r[0].strip() == "Data Lanc.") + 1
    for r in all_rows[start:]:
        if len(r) < 5 or not r[0].strip():
            continue
        value = amount(r[3])
        if value is not None and value < 0:
            add_expense(rows, bank="ActivoBank", kind="Conta à ordem", statement_month=statement_month, tx_date=parse_date(r[0]), description=r[2], value=abs(value), source=source)
    return rows


def parse_cgd_account(path: Path, statement_month: str, source: str) -> list[Expense]:
    rows: list[Expense] = []
    all_rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))
    start = next(i for i, r in enumerate(all_rows) if r and r[0].strip() == "Data mov.") + 1
    for r in all_rows[start:]:
        if len(r) < 8 or not r[0].strip():
            continue
        debit = amount(r[3])
        if debit is not None and debit > 0:
            add_expense(rows, bank="CGD", kind="Conta à ordem", statement_month=statement_month, tx_date=parse_date(r[0]), description=r[2], value=debit, source=source)
    return rows


ACCOUNT_PARSERS = {
    "activobank": parse_activobank_account,
    "cgd": parse_cgd_account,
}


def load_sheet_values(spreadsheet_id: str, range_a1: str, account: str) -> list[list[str]]:
    raw = gog(["sheets", "get", spreadsheet_id, range_a1, "--json"], account)
    return json.loads(raw).get("values", [])


def load_rules(spreadsheet_id: str, account: str) -> list[Rule]:
    values = load_sheet_values(spreadsheet_id, RULES_RANGE, account)
    rules: list[Rule] = []
    for row_num, row in enumerate(values[1:], start=2):
        row = (row + [""] * 9)[:9]
        active, priority, text, value, match_type, bank, kind, category, notes = row
        if norm(active) not in {"sim", "yes", "true", "1", "s"}:
            continue
        if not text.strip() or norm(text).startswith("exemplo:"):
            continue
        try:
            priority_int = int(float(str(priority).replace(",", "."))) if str(priority).strip() else 0
        except ValueError:
            priority_int = 0
        rules.append(Rule(row=row_num, active=True, priority=priority_int, text=text.strip(), value=amount(value), match_type=norm(match_type) or "contem", bank=bank.strip(), kind=kind.strip(), category=category.strip(), notes=notes.strip()))
    return sorted(rules, key=lambda r: (r.priority, r.row), reverse=True)


def rule_matches(rule: Rule, exp: Expense) -> bool:
    if rule.bank and norm(exp.bank) != norm(rule.bank):
        return False
    if rule.kind and norm(exp.kind) != norm(rule.kind):
        return False
    if rule.value is not None and round(exp.value, 2) != rule.value:
        return False
    desc = norm(exp.description)
    text = norm(rule.text)
    match_type = norm(rule.match_type)
    if match_type in {"contem", "contém", "contains"}:
        return text in desc
    if match_type in {"igual", "igual a", "equals", "exacto", "exato"}:
        return text == desc
    if match_type in {"comeca com", "começa com", "starts with"}:
        return desc.startswith(text)
    return text in desc


def infer_category(exp: Expense) -> str:
    """High-confidence fallback categorisation used only after user rules.

    User-maintained rules from `Regras Catalogacao` always win. These fallbacks
    are intentionally conservative and leave ambiguous transfers/payments blank.
    """
    d = norm(exp.description)
    if any(x in d for x in ["via verde"]):
        return "Viaturas - Via Verde"
    if any(x in d for x in ["petrogal", "repsol", "est servico", "postos combustivel", "a s freixo"]):
        return "Viaturas - Combustível"
    if any(x in d for x in ["imposto do selo"]):
        return "Impostos e Taxas"
    if any(x in d for x in ["zurich", "ocidental", "generali", "seguro viagem"]):
        return "Seguros"
    if any(x in d for x in ["edp comercial", "gold energy", "aldro energia", "aguas e energia"]):
        return "Casa - Contas"
    if any(x in d for x in ["pag.prestacao", "cobranca prestacao", "credibom"]):
        return "Casa - Empréstimo"
    if "solinca" in d:
        return "Ginásio e bem estar"
    if any(x in d for x in ["farmacia", "farmara", "tl sao joao", "fcia inigo"]):
        return "Saúde"
    if any(x in d for x in ["metro de madrid", "aerop", "uber", "ubr pe", "air europa"]):
        return "Viagens"
    if any(x in d for x in ["disney", "apple.com/bill"]):
        return "Subscrições"
    if any(x in d for x in ["resident advisor", "live music lab", "fnac", "porto editora"]):
        return "Entretenimento"
    if any(x in d for x in ["ikea", "leroy merlin", "sklum"]):
        return "Casa - Eletrodomésticos/Mobília"
    if any(x in d for x in ["zara", "primark", "sport zone", "mo espaco"]):
        return "Vestuário"
    if "motocard" in d:
        return "Hobbies"
    if "barbeiro" in d:
        return "Ginásio e bem estar"
    if any(x in d for x in ["glovo", "que larica", "confeitaria", "cafe expresso", "tasco do luis", "vicios de mesa", "churrasqueira", "h3 campus", "pez tortilla", "citywok", "arde br", "captain", "torrons", "la esqu", "cafe ta", "pez tor"]):
        return "Restauração"
    if any(x in d for x in ["auchan", "continente", "mercadona", "lidl", "alcampo", "mercado", "aliment", "super 2000", "gondomac"]):
        return "Alimentação"
    if "primor" in d:
        return "Casa - Limpeza"
    if any(x in d for x in ["bonjour", "zara.com"]):
        return "Compras Online"
    if "levantamento" in d or d.startswith("lev atm"):
        return "ATM"
    return ""


def apply_rules(expenses: list[Expense], rules: list[Rule]) -> Counter[str]:
    matched: Counter[str] = Counter()
    for exp in expenses:
        applied_rule = False
        for rule in rules:
            if rule_matches(rule, exp):
                exp.category = rule.category
                matched[f"rule row {rule.row}: {rule.text} -> {rule.category or '(blank)'}"] += 1
                applied_rule = True
                break
        if not applied_rule:
            exp.category = infer_category(exp)
            if exp.category:
                matched[f"fallback -> {exp.category}"] += 1
    return matched


def discover_and_parse(folder_id: str, account: str, workdir: Path) -> tuple[list[Expense], dict[str, Any]]:
    files = list_folder(folder_id, account)
    expenses: list[Expense] = []
    skipped: list[str] = []
    parsed_files: Counter[str] = Counter()

    for file in sorted(files, key=lambda f: f.name):
        parsed = parse_source_name(file.name)
        if not parsed:
            continue
        bank, source_type, statement_month = parsed
        bank_key = norm(bank)
        target = workdir / file.name
        download(file, target, account)
        before = len(expenses)
        try:
            if source_type == "card_pdf":
                parser = CARD_PARSERS.get(bank_key)
                if not parser:
                    skipped.append(f"{file.name}: unsupported card PDF bank")
                    continue
                text = pdf_to_text(target)
                expenses.extend(parser(text, statement_month, file.name))
            else:
                parser = ACCOUNT_PARSERS.get(bank_key)
                if not parser:
                    skipped.append(f"{file.name}: unsupported account CSV bank")
                    continue
                expenses.extend(parser(target, statement_month, file.name))
        except Exception as exc:  # keep processing other files and report the problem
            skipped.append(f"{file.name}: {exc}")
            continue
        parsed_files[file.name] = len(expenses) - before

    metadata = {"parsed_files": dict(parsed_files), "skipped": skipped}
    return expenses, metadata


def rows_for_sheet(expenses: list[Expense]) -> list[list[Any]]:
    ordered = sorted(expenses, key=lambda e: (e.statement_month, e.tx_date, e.bank, e.kind, e.source, e.description, e.value))
    return [MOV_HEADERS] + [[e.bank, e.kind, e.statement_month, google_serial(e.tx_date), e.description, e.value, e.category, e.source] for e in ordered]


def update_sheet(spreadsheet_id: str, rows: list[list[Any]], account: str) -> None:
    gog(["drive", "rename", spreadsheet_id, TARGET_TITLE, "--json"], account)
    total_rows = len(rows)
    values_json = json.dumps(rows, ensure_ascii=False)
    gog(["sheets", "clear", spreadsheet_id, "Movimentos!A:K", "--json"], account)
    gog(["sheets", "update", spreadsheet_id, f"Movimentos!A1:H{total_rows}", "--values-json", values_json, "--input", "RAW", "--json"], account)
    if total_rows > 1:
        gog(["sheets", "number-format", spreadsheet_id, f"Movimentos!D2:D{total_rows}", "--type", "DATE", "--pattern", "yyyy-mm-dd", "--json"], account)
        gog(["sheets", "number-format", spreadsheet_id, f"Movimentos!F2:F{total_rows}", "--type", "NUMBER", "--pattern", "0.00", "--json"], account)
    # Best effort formatting.
    try:
        gog(["sheets", "freeze", spreadsheet_id, "--sheet", "Movimentos", "--rows", "1", "--json"], account)
        gog(["sheets", "resize-columns", spreadsheet_id, "Movimentos!A:H", "--auto", "--json"], account)
    except subprocess.CalledProcessError:
        pass


def summarise(expenses: list[Expense], metadata: dict[str, Any], rule_matches: Counter[str]) -> dict[str, Any]:
    by_month = Counter(e.statement_month for e in expenses)
    by_bank_type = Counter((e.bank, e.kind) for e in expenses)
    by_source = Counter(e.source for e in expenses)
    categorised = sum(1 for e in expenses if e.category)
    return {
        "total_expenses": len(expenses),
        "categorised": categorised,
        "uncategorised": len(expenses) - categorised,
        "by_month": dict(sorted(by_month.items())),
        "by_bank_type": {f"{bank} / {kind}": count for (bank, kind), count in sorted(by_bank_type.items())},
        "by_source": dict(sorted(by_source.items())),
        "rule_matches": dict(rule_matches),
        "parsed_files": metadata["parsed_files"],
        "skipped": metadata["skipped"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder-id", default=DEFAULT_FOLDER_ID)
    parser.add_argument("--spreadsheet-id", default=DEFAULT_SPREADSHEET_ID)
    parser.add_argument("--account", default=DEFAULT_ACCOUNT)
    parser.add_argument("--summary-out", type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="expense-source-") as tmp:
        expenses, metadata = discover_and_parse(args.folder_id, args.account, Path(tmp))
    rules = load_rules(args.spreadsheet_id, args.account)
    matched_rules = apply_rules(expenses, rules)
    rows = rows_for_sheet(expenses)
    update_sheet(args.spreadsheet_id, rows, args.account)
    summary = summarise(expenses, metadata, matched_rules)
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.summary_out:
        args.summary_out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
