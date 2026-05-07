#!/usr/bin/env python3
"""Parse January 2026 card statement movements from ActivoBank and CGD PDF text exports."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"


def amount_pt(value: str) -> str:
    """Normalize Portuguese/statement amount string to decimal point."""
    value = value.strip().replace(" ", "")
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    return f"{float(value):.2f}"


def date_slash(value: str) -> str:
    y, m, d = value.split("/")
    return f"{y}-{m}-{d}"


def parse_activo(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    lines = text.splitlines()
    capture = False
    pending: list[str] | None = None
    for raw in lines:
        line = " ".join(raw.split())
        if not capture:
            if line == "DETALHE DOS MOVIMENTOS":
                capture = True
            continue
        if not line or line.startswith("Pág.") or "www.activobank.pt" in line:
            continue
        if line in {"Data Data", "Movimento Valor Descritivo Rede Débito Crédito"}:
            continue
        if line == "VIS" and pending:
            pending[6] = "VIS"
            continue

        m = re.match(r"^(\d{4}/\d{2}/\d{2})\s+(\d{4}/\d{2}/\d{2})\s+(.+?)\s+([0-9]+(?:[.,][0-9]{2}))$", line)
        if not m:
            continue
        data_mov, data_valor, desc, amt = m.groups()
        desc = desc.strip()
        value = amount_pt(amt)
        is_credit = desc.startswith(">")
        row = [
            "ActivoBank",
            "2026-01",
            date_slash(data_mov),
            date_slash(data_valor),
            "",
            desc,
            "",
            "" if is_credit else value,
            value if is_credit else "",
            "EUR",
            "ActivoBank-ExtratoCartao-202601.pdf",
        ]
        rows.append(row)
        pending = row
    return rows


def parse_cgd(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    lines = text.splitlines()

    # Account-card movements: Dt. Ord. Pag., Data Valor, Data Trans., ref, description, debit, credit.
    for raw in lines:
        line = " ".join(raw.split())
        m = re.match(
            r"^(\d{4}-\d{2}-\d{2})\s+(\d{4}-\d{2}-\d{2})\s+(\d{4}-\d{2}-\d{2})\s+\d+\s+(.+?)\s+([0-9]+,[0-9]{2})\s+([0-9]+,[0-9]{2})$",
            line,
        )
        if m:
            data_mov, data_valor, data_trans, desc, deb, cred = m.groups()
            rows.append([
                "CGD",
                "2026-01",
                data_mov,
                data_valor,
                data_trans,
                desc.strip(),
                "",
                amount_pt(deb) if float(amount_pt(deb)) else "",
                amount_pt(cred) if float(amount_pt(cred)) else "",
                "EUR",
                "CGD-ExtratoCartao-202601.pdf",
            ])

    # Card purchase movements: transaction date, description, debit, credit.
    for raw in lines:
        line = " ".join(raw.split())
        m = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(.+?)\s+([0-9]+,[0-9]{2})\s+([0-9]+,[0-9]{2})$", line)
        if not m:
            continue
        data_trans, desc, deb, cred = m.groups()
        if desc.startswith("Saldo Cred") or desc.startswith("Extrato"):
            continue
        # Avoid duplicating the account movement parsed above.
        if "PAGAMENTO AUTOMATICO" in desc:
            continue
        rows.append([
            "CGD",
            "2026-01",
            data_trans,
            "",
            data_trans,
            desc.strip(),
            "",
            amount_pt(deb) if float(amount_pt(deb)) else "",
            amount_pt(cred) if float(amount_pt(cred)) else "",
            "EUR",
            "CGD-ExtratoCartao-202601.pdf",
        ])
    return rows


headers = [
    "Banco",
    "MesExtrato",
    "DataMovimento",
    "DataValor",
    "DataTransacao",
    "Descritivo",
    "RedePais",
    "Debito",
    "Credito",
    "Moeda",
    "FontePDF",
]

activo = parse_activo((DATA / "ActivoBank-ExtratoCartao-202601.txt").read_text(encoding="utf-8"))
cgd = parse_cgd((DATA / "CGD-ExtratoCartao-202601.txt").read_text(encoding="utf-8"))
rows = [headers] + activo + cgd

(DATA / "january-card-movements.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
with (DATA / "january-card-movements.csv").open("w", encoding="utf-8", newline="") as f:
    csv.writer(f).writerows(rows)

print(json.dumps({"activo_rows": len(activo), "cgd_rows": len(cgd), "total_rows": len(rows) - 1}, ensure_ascii=False))
