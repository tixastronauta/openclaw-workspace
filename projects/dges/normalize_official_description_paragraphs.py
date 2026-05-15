#!/usr/bin/env python3
"""Normalize DGES course_description_official cells to exactly three paragraphs."""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import random
import re
import subprocess
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

SHEET_ID = "1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E"
TAB = "dges_cursos_2026"
DEFAULT_ACCOUNT = "tiago.carvalho@gmail.com"
TARGET_HEADER = "course_description_official"
DATA_DIR = Path("projects/dges/data")
CACHE_PATH = DATA_DIR / "course_description_official_cache.json"
REPORT_PATH = DATA_DIR / "course_description_official_paragraph_normalization_report.json"
LOG_PATH = DATA_DIR / "course_description_official_paragraph_normalization.log"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("OPENROUTER_DGES_MODEL", "openai/gpt-4.1-mini")
MAX_DESCRIPTION_CHARS = 1400

BAD_FRAGMENT_RE = re.compile(r"\b(objetivos|objectivos),|dota-los|pretende,? também|;\.|,\.|:\.|cookies?|javascript|linkedin|provas de ingresso", re.I)


def now_lisbon() -> str:
    return dt.datetime.now(ZoneInfo("Europe/Lisbon")).strftime("%Y-%m-%d %H:%M:%S %Z")


def log(msg: str) -> None:
    line = f"[{now_lisbon()}] {msg}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def sh(args: list[str]) -> str:
    return subprocess.check_output(args, text=True)


def gog_base(account: str) -> list[str]:
    return ["gog", "sheets", "--account", account]


def get_sheet(account: str) -> list[list[str]]:
    return json.loads(sh(gog_base(account) + ["get", SHEET_ID, f"{TAB}!A1:AZ2000", "--json", "--no-input"]))["values"]


def update_range(account: str, a1_range: str, values: list[list[str]]) -> None:
    subprocess.run(
        gog_base(account)
        + ["update", SHEET_ID, a1_range, "--values-json", json.dumps(values, ensure_ascii=False), "--input", "USER_ENTERED", "--no-input"],
        check=True,
    )


def col_letter(index_1_based: int) -> str:
    out = ""
    n = index_1_based
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def clean(text: str) -> str:
    text = (text or "").replace("\xa0", " ").replace("\u200b", " ").replace("\ufeff", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip(" \t\n\r-–—|•")


def paragraphs(text: str) -> list[str]:
    return [clean(p) for p in re.split(r"\n\s*\n+", text.strip()) if clean(p)]


def paragraph_count(text: str) -> int:
    return len(paragraphs(text))


def row_value(row: list[str], idx: dict[str, int], key: str) -> str:
    i = idx.get(key, -1)
    return clean(row[i]) if i >= 0 and i < len(row) else ""


def fit_description(desc: str) -> str:
    """Keep exactly 3 paragraphs while enforcing the hard character cap."""
    ps = paragraphs(desc)
    if len(ps) != 3 or len(desc) <= MAX_DESCRIPTION_CHARS:
        return desc

    def sentences(p: str) -> list[str]:
        return [clean(s) for s in re.split(r"(?<=[.!?])\s+", p) if clean(s)]

    chunks = [sentences(p) or [p] for p in ps]
    # Prefer removing trailing detail sentences while keeping at least one sentence per paragraph.
    while len("\n\n".join(" ".join(c) for c in chunks)) > MAX_DESCRIPTION_CHARS and any(len(c) > 1 for c in chunks):
        candidates = [(len(c[-1]), i) for i, c in enumerate(chunks) if len(c) > 1]
        _, i = max(candidates)
        chunks[i].pop()

    fitted = "\n\n".join(" ".join(c) for c in chunks)
    if len(fitted) <= MAX_DESCRIPTION_CHARS:
        return fitted

    # Last resort: trim each paragraph safely, preserving final punctuation.
    budget = (MAX_DESCRIPTION_CHARS - 4) // 3
    trimmed = []
    for p in [" ".join(c) for c in chunks]:
        if len(p) > budget:
            p = p[:budget].rsplit(" ", 1)[0].rstrip(",;:") + "."
        trimmed.append(p)
    return "\n\n".join(trimmed).strip()


def quality_flags(desc: str) -> list[str]:
    flags = []
    ps = paragraphs(desc)
    if len(ps) != 3:
        flags.append(f"paragraphs_{len(ps)}")
    if not desc or len(desc) < 280:
        flags.append("too_short")
    if len(desc) > MAX_DESCRIPTION_CHARS:
        flags.append("too_long")
    if BAD_FRAGMENT_RE.search(desc or ""):
        flags.append("bad_fragment")
    if any(len(s) > 480 for s in re.split(r"(?<=[.!?])\s+", desc or "")):
        flags.append("long_sentence")
    return flags


def cache_key(row: list[str], idx: dict[str, int]) -> str:
    return f"{row_value(row, idx, 'institution_code')}::{row_value(row, idx, 'course_code')}"


def compact_source(cache_result: dict) -> str:
    parts = []
    sample = cache_result.get("official_excerpt_sample") or ""
    if sample:
        parts.append("Excerto oficial selecionado:\n" + sample[:1400])
    pieces = cache_result.get("official_pieces") or []
    if pieces:
        parts.append("Notas oficiais úteis:\n" + "\n".join(f"- {p}" for p in pieces[:5])[:1600])
    sources = cache_result.get("sources") or []
    dges = [s for s in sources if s.get("type") == "dges"]
    if dges:
        parts.append("Metadados DGES:\n" + json.dumps(dges[0].get("meta", {}), ensure_ascii=False))
    return "\n\n".join(parts)[:3500]


def normalize_with_llm(row: list[str], idx: dict[str, int], current: str, cache_result: dict, model: str, timeout: int = 60) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    facts = {
        "course": row_value(row, idx, "course_name"),
        "cycle": row_value(row, idx, "cycle"),
        "institution": row_value(row, idx, "institution_name_full") or row_value(row, idx, "institution_name"),
        "city": row_value(row, idx, "cidade"),
        "district": row_value(row, idx, "distrito"),
    }
    system = (
        "És um editor académico português. Reescreves descrições de cursos em PT-PT, "
        "mantendo rigor factual e sem inventar detalhes."
    )
    user = f"""
Reescreve a descrição abaixo para ter EXATAMENTE 3 parágrafos curtos, separados por uma linha em branco.

Regras obrigatórias:
- Exatamente 3 parágrafos; não uses listas, títulos, tabelas, URLs, citações ou disclaimers.
- Mantém PT-PT e tom institucional claro.
- Mantém **negrito** nos factos principais.
- Entre 750 e 1300 caracteres; nunca ultrapasses {MAX_DESCRIPTION_CHARS} caracteres.
- Usa apenas a descrição atual, metadados e excertos abaixo; não inventes factos.
- Remove formulações estranhas como "objetivos," e frases partidas; escreve, por exemplo, "objetivos e contextos".
- Estrutura recomendada:
  1) identificação do curso, instituição, ciclo/duração/ECTS/localização quando disponível;
  2) áreas, competências e conteúdos principais;
  3) preparação académica/profissional suportada e enquadramento do curso.

Metadados da folha:
{json.dumps(facts, ensure_ascii=False, indent=2)}

Descrição atual:
{current}

Fontes/cache usados originalmente:
{compact_source(cache_result) or "(sem fonte adicional no cache)"}
""".strip()
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.15,
        "max_tokens": 520,
    }
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://openclaw.local",
            "X-Title": "OpenClaw DGES paragraph normalization",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = data["choices"][0]["message"]["content"].strip()
    text = re.sub(r"^```(?:markdown)?|```$", "", text, flags=re.I).strip()
    ps = paragraphs(text)
    return fit_description("\n\n".join(ps).strip())


def contiguous_groups(pending: dict[int, str], max_rows: int = 40) -> list[tuple[int, int, list[list[str]]]]:
    groups = []
    start = last = None
    vals: list[list[str]] = []
    for row in sorted(pending):
        if start is None or last is None or row != last + 1 or len(vals) >= max_rows:
            if start is not None and last is not None:
                groups.append((start, last, vals))
            start = row
            vals = []
        vals.append([pending[row]])
        last = row
    if start is not None and last is not None:
        groups.append((start, last, vals))
    return groups


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=DEFAULT_ACCOUNT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--include-bad-fragment", action="store_true")
    parser.add_argument("--all-flags", action="store_true", help="Normalize every row with any quality flag, not just paragraph-count issues.")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_PATH.exists():
        LOG_PATH.write_text("", encoding="utf-8")

    values = get_sheet(args.account)
    headers = values[0]
    idx = {h: i for i, h in enumerate(headers)}
    target_col = col_letter(idx[TARGET_HEADER] + 1)
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {"results": {}}

    candidates = []
    for sheet_row, row in enumerate(values[1:], start=2):
        current = row_value(row, idx, TARGET_HEADER)
        if not current:
            continue
        flags = quality_flags(current)
        needs = bool(flags) if args.all_flags else (any(f.startswith("paragraphs_") for f in flags) or (args.include_bad_fragment and "bad_fragment" in flags))
        if needs:
            candidates.append((sheet_row, row, current, flags))
    if args.limit:
        candidates = candidates[: args.limit]

    log(f"starting paragraph normalization rows={len(candidates)} write={args.write} workers={args.workers} model={args.model}")
    pending: dict[int, str] = {}
    details: dict[int, dict] = {}
    counters = {"processed": 0, "prepared": 0, "errors": 0, "flagged_after": 0}

    def work(item):
        sheet_row, row, current, before_flags = item
        ck = cache_key(row, idx)
        cache_result = cache.get("results", {}).get(ck, {})
        last_error = None
        for attempt in range(3):
            try:
                desc = normalize_with_llm(row, idx, current, cache_result, args.model)
                after_flags = quality_flags(desc)
                if not after_flags:
                    return sheet_row, desc, before_flags, after_flags
                last_error = f"validation failed attempt {attempt + 1}: {after_flags}"
                current = desc
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(random.uniform(0.4, 1.2))
        return sheet_row, current, before_flags, quality_flags(current), last_error

    with cf.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(work, item) for item in candidates]
        for n, fut in enumerate(cf.as_completed(futures), start=1):
            try:
                result = fut.result()
            except Exception as exc:
                counters["errors"] += 1
                log(f"[{n}/{len(candidates)}] ERROR {type(exc).__name__}: {exc}")
                continue
            sheet_row, desc, before_flags, after_flags, *rest = result
            err = rest[0] if rest else None
            counters["processed"] += 1
            if desc:
                pending[sheet_row] = desc
                counters["prepared"] += 1
            if after_flags:
                counters["flagged_after"] += 1
            details[sheet_row] = {"before_flags": before_flags, "after_flags": after_flags, "error": err, "chars": len(desc)}
            if n % 10 == 0 or n == len(candidates):
                REPORT_PATH.write_text(json.dumps({"generated": now_lisbon(), "write": args.write, "counters": counters, "details": details}, ensure_ascii=False, indent=2), encoding="utf-8")
            log(f"[{n}/{len(candidates)}] row {sheet_row} chars={len(desc)} before={before_flags} after={after_flags}")

    if args.write and pending:
        log(f"writing {len(pending)} cells to {target_col}")
        for start, end, vals in contiguous_groups(pending):
            rng = f"{TAB}!{target_col}{start}:{target_col}{end}"
            update_range(args.account, rng, vals)
            log(f"updated {rng} ({len(vals)} rows)")
            time.sleep(random.uniform(0.4, 0.9))

    REPORT_PATH.write_text(json.dumps({"generated": now_lisbon(), "write": args.write, "rows": len(candidates), "prepared": len(pending), "counters": counters, "details": details}, ensure_ascii=False, indent=2), encoding="utf-8")
    log("done :: " + json.dumps(counters, ensure_ascii=False))
    return 0 if counters["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
