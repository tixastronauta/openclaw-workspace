#!/usr/bin/env python3
"""Populate course_description_official from official/public sources.

Source priority:
1. Official course page from the sheet (course_url)
2. Official DGES course detail page (detalhes_do_curso) for facts
3. Wikipedia summary only as a conservative fallback/context source

The script writes only the course_description_official column. It keeps an audit
cache with source URLs, extracted excerpts, and generation metadata.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import html as html_lib
import json
import os
import random
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

SHEET_ID = "1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E"
TAB = "dges_cursos_2026"
DEFAULT_ACCOUNT = "tiago.carvalho@gmail.com"
TARGET_HEADER = "course_description_official"
DATA_DIR = Path("projects/dges/data")
CACHE_PATH = DATA_DIR / "course_description_official_cache.json"
SEARCH_CACHE_PATH = DATA_DIR / "course_description_official_search_cache.json"
REPORT_PATH = DATA_DIR / "course_description_official_report.json"
LOG_PATH = DATA_DIR / "course_description_official.log"
USER_AGENT = "Mozilla/5.0 (compatible; Nyx DGES official course descriptions; source-based summaries)"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("OPENROUTER_DGES_MODEL", "openai/gpt-4.1-mini")
MAX_DESCRIPTION_CHARS = 1400

BAD_MARKERS = [
    "cookie", "cookies", "javascript", "newsletter", "menu", "404", "not found", "não encontrada",
    "acessibilidade", "mapa do site", "facebook", "instagram", "linkedin", "erasmus", "evento",
    "seminário", "workshop", "notícia", "noticias", "news", "horários", "calendário",
    "legislação", "regulamentos", "órgãos de gestão", "corpo docente", "guia do estudante",
    "unidade curricular", "responsável da unidade", "programa da disciplina", "ob1:", "ob2:", "cp1:",
    "provas de ingresso", "classificações mínimas", "pré-requisitos", "contingente", "propinas",
]
GOOD_ANCHORS = [
    "Apresentação", "Apresentacao", "Objetivos", "Objectivos", "Caracterização", "Caracterizacao",
    "O Curso", "Sobre o Curso", "Descrição", "Descricao", "Competências", "Competencias",
    "Saídas Profissionais", "Saidas Profissionais", "Perfil", "Empregabilidade", "Objetivo",
    "Porquê", "Porque estudar", "O que vais aprender", "Áreas", "Areas",
]
STOP_MARKERS = [
    "Plano de estudos", "Plano curricular", "Estrutura curricular", "Unidades curriculares",
    "Candidaturas", "Condições de acesso", "Acesso", "Propinas", "Contactos", "Horário",
    "1º ANO", "1.º ANO", "1 ANO", "Regime", "Calendário", "Documentos", "Mais informação",
    "Testemunhos", "Testemunho", "Alumni", "Perfil LinkedIn", "Perfil Ciência Vitae",
]


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def now_lisbon() -> str:
    return dt.datetime.now(ZoneInfo("Europe/Lisbon")).strftime("%Y-%m-%d %H:%M:%S %Z")


def log(msg: str) -> None:
    line = f"[{now_lisbon()}] {msg}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def clean(text: str) -> str:
    text = html_lib.unescape(text or "")
    text = text.replace("\xa0", " ").replace("\u200b", " ").replace("\ufeff", " ")
    text = re.sub(r"\s+", " ", text).strip(" \t\n\r-–—|•")
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([.!?]){2,}", r"\1", text)
    return text


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


def row_value(row: list[str], idx: dict[str, int], key: str) -> str:
    i = idx.get(key, -1)
    return clean(row[i]) if i >= 0 and i < len(row) else ""


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch(url: str, timeout: int = 14) -> str:
    if not url or not url.lower().startswith(("http://", "https://")):
        return ""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.5"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read(2_000_000)
    for enc in ("utf-8", "iso-8859-1", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def root_domain(url: str) -> str:
    try:
        host = urllib.parse.urlparse(url).netloc.casefold().split(":", 1)[0]
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def brave_search(query: str, count: int = 8, timeout: int = 20) -> list[dict]:
    key = os.environ.get("BRAVE_API_KEY")
    if not key:
        return []
    # Keep ui_lang=en-US per workspace preference. Avoid country/search_lang
    # filters here: for Portuguese institutional pages Brave returns better
    # official-site hits without narrowing the index.
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": query, "count": count, "ui_lang": "en-US"})
    req = urllib.request.Request(url, headers={"Accept": "application/json", "X-Subscription-Token": key})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("web", {}).get("results", []) or []


def search_official_candidates(row: list[str], idx: dict[str, int], search_cache: dict) -> list[str]:
    course = row_value(row, idx, "course_name")
    inst = row_value(row, idx, "institution_name")
    inst_url = row_value(row, idx, "institution_url")
    domain = root_domain(inst_url)
    cache_key = f"{row_value(row, idx, 'institution_code')}::{row_value(row, idx, 'course_code')}::{domain}"
    if cache_key in search_cache:
        return search_cache[cache_key]
    queries = []
    if domain:
        queries.append(f'site:{domain} "{course}"')
        words = " ".join(re.findall(r"[A-Za-zÀ-ÿ0-9]+", course)[:6])
        if words and words != course:
            queries.append(f"site:{domain} {words}")
    queries.append(f'"{course}" "{inst}"')
    urls: list[str] = []
    seen = set()
    for q in queries:
        try:
            for item in brave_search(q):
                url = item.get("url", "")
                if not url or url in seen:
                    continue
                seen.add(url)
                low = url.casefold()
                if any(low.endswith(ext) for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip"]):
                    continue
                if domain and domain not in root_domain(url):
                    # Search can return social/wiki/etc.; keep this function official-domain only.
                    continue
                urls.append(url)
                if len(urls) >= 5:
                    break
        except Exception:
            continue
        if len(urls) >= 5:
            break
    search_cache[cache_key] = urls
    return urls


def strip_tags(html: str) -> str:
    html = re.sub(r"<(?P<tag>script|style|noscript|svg|nav|footer|header|form|aside)[^>]*>.*?</(?P=tag)>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    html = re.sub(r"<br\s*/?>", ". ", html, flags=re.I)
    html = re.sub(r"</(p|div|li|h[1-6]|td|tr|section|article)>", ". ", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return clean(html)


def meta_descriptions(html: str) -> list[str]:
    out = []
    for m in re.finditer(r"<meta[^>]+(?:name|property)=[\"'](?:description|og:description|twitter:description)[\"'][^>]+content=[\"'](.*?)[\"']", html, flags=re.S | re.I):
        s = clean(m.group(1))
        if s:
            out.append(s)
    return out


def sentence_split(text: str) -> list[str]:
    text = clean(text)
    pieces = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for p in pieces:
        p = clean(p)
        if 80 <= len(p) <= 500:
            out.append(p)
    return out


def reject_piece(s: str) -> bool:
    low = s.casefold()
    if any(b in low for b in BAD_MARKERS):
        return True
    if re.search(r"\b(onde|de|para|com|em|e|ou)\.$", low):
        return True
    if re.match(r"^(objetivos|objectivos|competências|saídas|incluindo|permitindo)[,;:]?\s*$", low):
        return True
    if sum(ch.isdigit() for ch in s) > max(10, len(s) * 0.22):
        return True
    if len(re.findall(r"\.", s)) > 8:
        return True
    return False


def trim_at_stop(text: str) -> str:
    low = text.casefold()
    positions = []
    for marker in STOP_MARKERS:
        pos = low.find(marker.casefold())
        if pos > 120:
            positions.append(pos)
    if positions:
        text = text[: min(positions)]
    return clean(text)


def extract_official_excerpt(html: str, course_name: str) -> tuple[str, list[str]]:
    text = strip_tags(html)
    if not text:
        return "", []
    candidates: list[str] = []
    candidates.extend(meta_descriptions(html))
    anchors = []
    needles = GOOD_ANCHORS + [course_name]
    low_text = text.casefold()
    for needle in needles:
        start = 0
        while needle and len(anchors) < 24:
            pos = low_text.find(needle.casefold(), start)
            if pos < 0:
                break
            anchors.append(pos)
            start = pos + len(needle)
    if not anchors:
        anchors = [0]
    for pos in sorted(set(anchors))[:18]:
        chunk = trim_at_stop(text[pos : pos + 2400])
        candidates.extend(sentence_split(chunk))
    course_tokens = [t.casefold() for t in re.findall(r"[A-Za-zÀ-ÿ]{5,}", course_name)[:7]]
    scored = []
    seen = set()
    for s in candidates:
        s = re.sub(r"\s*\|\s*", ", ", clean(s))
        key = re.sub(r"\W+", "", s.casefold())[:140]
        if not s or key in seen or reject_piece(s):
            continue
        seen.add(key)
        low = s.casefold()
        score = 0
        score += sum(3 for t in course_tokens if t in low)
        score += sum(2 for w in ["objetivo", "competência", "forma", "prepara", "pretende", "perfil", "profissional", "projeto", "multimédia", "design", "engenharia", "gestão", "saúde"] if w in low)
        if 120 <= len(s) <= 320:
            score += 2
        if any(w in low for w in ["candidatura", "plano", "propina", "contacto", "horário"]):
            score -= 4
        if score >= 2:
            scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = []
    total = 0
    for _score, s in scored:
        if total + len(s) > 2200 and selected:
            break
        selected.append(s)
        total += len(s)
        if len(selected) >= 7:
            break
    return "\n".join(selected), selected


def dges_field(text: str, label: str, stop_labels: list[str]) -> str:
    pattern = re.escape(label) + r":?\s*(.*?)\s*(?=" + "|".join(re.escape(s) + r":?" for s in stop_labels) + r"|$)"
    m = re.search(pattern, text, flags=re.S | re.I)
    return clean(m.group(1)) if m else ""


def parse_dges_meta(html: str) -> dict[str, str]:
    text = strip_tags(html)
    area = dges_field(text, "Área CNAEF", ["Duração", "ECTS", "Tipo de Ensino", "Concurso"])
    area = re.sub(r"^\d+\s+", "", area).strip()
    return {
        "area": area,
        "duration": dges_field(text, "Duração", ["ECTS", "Tipo de Ensino", "Concurso"]),
        "ects": dges_field(text, "ECTS", ["Tipo de Ensino", "Concurso", "Vagas"]),
        "teaching_type": dges_field(text, "Tipo de Ensino", ["Concurso", "Vagas", "Provas de Ingresso"]),
        "vacancies": dges_field(text, "Vagas para 2026-2027", ["Pré-Requisitos", "Provas de Ingresso", "Classificações Mínimas"]),
    }


def wikipedia_summary(course_name: str, institution: str, timeout: int = 10) -> tuple[str, str]:
    query = f"{course_name} {institution}"
    params = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": query, "format": "json", "utf8": 1, "srlimit": 3})
    url = f"https://pt.wikipedia.org/w/api.php?{params}"
    try:
        data = json.loads(fetch(url, timeout=timeout))
        hits = data.get("query", {}).get("search", [])
        if not hits:
            return "", ""
        title = hits[0].get("title", "")
        if not title:
            return "", ""
        summary_url = "https://pt.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title)
        summary = json.loads(fetch(summary_url, timeout=timeout))
        extract = clean(summary.get("extract", ""))
        page = summary.get("content_urls", {}).get("desktop", {}).get("page", "")
        if extract and any(tok.casefold() in extract.casefold() for tok in [course_name.split()[0], institution.split()[0]]):
            return extract[:1000], page
    except Exception:
        return "", ""
    return "", ""


def institution_display(row: list[str], idx: dict[str, int]) -> str:
    inst = row_value(row, idx, "institution_name")
    sigla = row_value(row, idx, "institution_sigla")
    parent = row_value(row, idx, "parent_institution_acronym")
    out = inst
    if sigla and sigla not in out:
        out += f" ({sigla})"
    if parent and parent not in out:
        out += f" / {parent}"
    return out


def source_quality(excerpt: str) -> str:
    if len(excerpt) >= 450:
        return "official_course_page"
    if len(excerpt) >= 180:
        return "official_course_page_limited"
    return "dges_or_fallback"


def llm_generate(row: list[str], idx: dict[str, int], meta: dict[str, str], official_excerpt: str, wiki_excerpt: str, wiki_url: str, model: str, timeout: int = 60) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    course = row_value(row, idx, "course_name")
    cycle = row_value(row, idx, "cycle")
    institution = institution_display(row, idx)
    city = row_value(row, idx, "cidade")
    district = row_value(row, idx, "distrito")
    facts = {
        "course": course,
        "cycle": cycle,
        "institution": institution,
        "area_cnaef": meta.get("area", ""),
        "city": city,
        "district": district,
        "duration": meta.get("duration", ""),
        "ects": meta.get("ects", ""),
        "teaching_type": meta.get("teaching_type", ""),
        "vacancies_2026_2027": meta.get("vacancies", ""),
        "official_course_url": row_value(row, idx, "course_url"),
        "dges_url": row_value(row, idx, "detalhes_do_curso"),
        "wikipedia_url": wiki_url,
    }
    system = (
        "És um editor académico português. Escreves descrições de cursos para candidatos que não conhecem o curso. "
        "Usa PT-PT, tom claro, institucional e útil. Não inventes factos que não estejam nos metadados ou excertos. "
        "Se os excertos oficiais forem pobres, sê conservador e usa os metadados DGES. Não menciones fontes no texto final."
    )
    user = f"""
Cria uma descrição pública para a coluna course_description_official.

Regras:
- 2 a 3 parágrafos curtos.
- Entre 600 e 1200 caracteres, máximo {MAX_DESCRIPTION_CHARS}.
- Markdown simples: usa **negrito** para nome do curso, instituição, área e factos principais.
- Deve explicar: o que é o curso, que áreas/competências trabalha, que tipo de preparação dá, e factos objetivos DGES.
- Não uses frases partidas dos excertos; reescreve com boa gramática.
- Não incluas URLs, citações, listas, tabelas, disclaimers ou "segundo".
- Não prometas empregabilidade nem saídas que não estejam suportadas.

Metadados DGES/folha:
{json.dumps(facts, ensure_ascii=False, indent=2)}

Excerto do site oficial do curso/instituição:
{official_excerpt[:4500] or "(sem excerto útil encontrado)"}

Excerto Wikipédia/outro público auxiliar:
{wiki_excerpt[:1200] or "(não usado)"}
""".strip()
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.2,
        "max_tokens": 450,
    }
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://openclaw.local",
            "X-Title": "OpenClaw DGES official descriptions",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = data["choices"][0]["message"]["content"]
    text = re.sub(r"^```(?:markdown)?|```$", "", text.strip(), flags=re.I).strip()
    return clean_description(text)


def clean_description(text: str) -> str:
    paragraphs = [clean(p) for p in re.split(r"\n\s*\n", text) if clean(p)]
    out = "\n\n".join(paragraphs)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    if len(out) > MAX_DESCRIPTION_CHARS:
        cut = out[:MAX_DESCRIPTION_CHARS]
        pieces = re.split(r"(?<=[.!?])\s+", cut)
        if len(pieces) > 1:
            out = " ".join(pieces[:-1]).strip()
        else:
            out = cut.rsplit(" ", 1)[0].strip() + "."
    return out


def quality_flags(desc: str) -> list[str]:
    flags = []
    if not desc or len(desc) < 280:
        flags.append("too_short")
    if len(desc) > MAX_DESCRIPTION_CHARS:
        flags.append("too_long")
    if any(p and re.match(r"^[a-záéíóúâêôãõç]", p.strip()) for p in desc.split("\n\n")):
        flags.append("lowercase_paragraph")
    if re.search(r"\b(objetivos|objectivos),|dota-los|pretende,? também|;\.|,\.|:\.|cookies?|javascript|linkedin|provas de ingresso", desc, re.I):
        flags.append("bad_fragment")
    if any(len(s) > 480 for s in re.split(r"(?<=[.!?])\s+", desc)):
        flags.append("long_sentence")
    return flags


def process_row(sheet_row: int, row: list[str], idx: dict[str, int], cache: dict, search_cache: dict, model: str, refresh: bool) -> tuple[int, dict]:
    key = f"{row_value(row, idx, 'institution_code')}::{row_value(row, idx, 'course_code')}"
    if not refresh and key in cache.get("results", {}):
        return sheet_row, cache["results"][key]
    course = row_value(row, idx, "course_name")
    result = {"course": course, "sources": [], "errors": [], "updatedAt": now_lisbon()}
    official_excerpt = ""
    official_pieces: list[str] = []
    meta: dict[str, str] = {}
    course_url = row_value(row, idx, "course_url")
    dges_url = row_value(row, idx, "detalhes_do_curso")
    try:
        if course_url:
            html = fetch(course_url)
            official_excerpt, official_pieces = extract_official_excerpt(html, course)
            result["sources"].append({"type": "official_course", "url": course_url, "excerpt_chars": len(official_excerpt)})
    except Exception as exc:
        result["errors"].append(f"course_url={type(exc).__name__}: {exc}")
    if len(official_excerpt) < 320:
        for candidate_url in search_official_candidates(row, idx, search_cache):
            if candidate_url == course_url:
                continue
            try:
                html = fetch(candidate_url)
                cand_excerpt, cand_pieces = extract_official_excerpt(html, course)
                result["sources"].append({"type": "official_search", "url": candidate_url, "excerpt_chars": len(cand_excerpt)})
                if len(cand_excerpt) > len(official_excerpt):
                    official_excerpt = cand_excerpt
                    official_pieces = cand_pieces
                    result["selected_official_url"] = candidate_url
                if len(official_excerpt) >= 700:
                    break
            except Exception as exc:
                result["errors"].append(f"search_url={type(exc).__name__}: {candidate_url}: {exc}")
    try:
        if dges_url:
            html = fetch(dges_url)
            meta = parse_dges_meta(html)
            result["sources"].append({"type": "dges", "url": dges_url, "meta": meta})
    except Exception as exc:
        result["errors"].append(f"dges={type(exc).__name__}: {exc}")
    wiki_excerpt = ""
    wiki_url = ""
    if len(official_excerpt) < 220:
        wiki_excerpt, wiki_url = wikipedia_summary(course, institution_display(row, idx))
        if wiki_excerpt:
            result["sources"].append({"type": "wikipedia", "url": wiki_url, "excerpt_chars": len(wiki_excerpt)})
    # Keep request rate civil and avoid synchronized bursts.
    time.sleep(random.uniform(0.05, 0.25))
    desc = llm_generate(row, idx, meta, official_excerpt, wiki_excerpt, wiki_url, model)
    result.update(
        {
            "description": desc,
            "chars": len(desc),
            "quality": source_quality(official_excerpt),
            "official_excerpt_chars": len(official_excerpt),
            "official_excerpt_sample": official_excerpt[:900],
            "official_pieces": official_pieces[:5],
            "quality_flags": quality_flags(desc),
            "model": model,
        }
    )
    cache.setdefault("results", {})[key] = result
    return sheet_row, result


def contiguous_groups(pending: dict[int, str], max_rows: int = 40) -> list[tuple[int, int, list[list[str]]]]:
    groups = []
    start = None
    last = None
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
    parser.add_argument("--limit", type=int)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--only-empty", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    if not LOG_PATH.exists():
        LOG_PATH.write_text("", encoding="utf-8")
    values = get_sheet(args.account)
    headers = values[0]
    idx = {h: i for i, h in enumerate(headers)}
    if TARGET_HEADER not in idx:
        raise SystemExit(f"Missing {TARGET_HEADER}; add the column first")
    target_col = col_letter(idx[TARGET_HEADER] + 1)
    required = ["course_code", "course_name", "institution_code", "course_url", "detalhes_do_curso", TARGET_HEADER]
    missing = [h for h in required if h not in idx]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    rows = list(enumerate(values[1:], start=2))
    if args.only_empty:
        rows = [(r, row) for r, row in rows if not row_value(row, idx, TARGET_HEADER)]
    if args.offset:
        rows = rows[args.offset:]
    if args.limit:
        rows = rows[: args.limit]

    cache = load_json(CACHE_PATH, {"results": {}})
    search_cache = load_json(SEARCH_CACHE_PATH, {})
    pending: dict[int, str] = {}
    details: dict[int, dict] = {}
    counters = {"processed": 0, "prepared": 0, "errors": 0, "flagged": 0}
    log(f"starting official descriptions rows={len(rows)} write={args.write} workers={args.workers} model={args.model}")

    with cf.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(process_row, sheet_row, row, idx, cache, search_cache, args.model, args.refresh) for sheet_row, row in rows]
        for n, fut in enumerate(cf.as_completed(futures), start=1):
            try:
                sheet_row, res = fut.result()
            except Exception as exc:
                counters["errors"] += 1
                log(f"[{n}/{len(rows)}] ERROR {type(exc).__name__}: {exc}")
                continue
            counters["processed"] += 1
            desc = res.get("description", "")
            flags = quality_flags(desc)
            if flags:
                counters["flagged"] += 1
            if desc:
                pending[sheet_row] = desc
                details[sheet_row] = res
                counters["prepared"] += 1
            if n % 10 == 0 or n == len(rows):
                save_json(CACHE_PATH, cache)
                save_json(SEARCH_CACHE_PATH, search_cache)
                save_json(REPORT_PATH, {"generated": now_lisbon(), "write": args.write, "counters": counters, "details": details})
            log(f"[{n}/{len(rows)}] row {sheet_row} {res.get('course')} chars={len(desc)} quality={res.get('quality')} flags={flags}")

    save_json(CACHE_PATH, cache)
    save_json(SEARCH_CACHE_PATH, search_cache)
    if args.write and pending:
        log(f"writing {len(pending)} cells to {target_col}")
        for start, end, vals in contiguous_groups(pending):
            rng = f"{TAB}!{target_col}{start}:{target_col}{end}"
            update_range(args.account, rng, vals)
            log(f"updated {rng} ({len(vals)} rows)")
            time.sleep(random.uniform(0.4, 0.9))

    report = {"generated": now_lisbon(), "write": args.write, "rows": len(rows), "prepared": len(pending), "counters": counters, "details": details}
    save_json(REPORT_PATH, report)
    log("done :: " + json.dumps(counters, ensure_ascii=False))
    return 0 if counters["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
