#!/usr/bin/env python3
"""Rewrite all course_description cells for the DGES course sheet.

Goal:
- rewrite every description, not only empty cells
- keep descriptions factual, <= 2000 chars, simple Markdown
- avoid source mentions, testimonials/opinions, menu/table garbage
- prefer official/institution course pages; use DGES metadata as fallback context
- fetch sources in parallel, but write to Google Sheets in controlled batches
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
import signal
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
DATA_DIR = Path("projects/dges/data")
LOG_PATH = DATA_DIR / "rewrite_course_descriptions.log"
PROGRESS_PATH = DATA_DIR / "rewrite_course_descriptions_progress.json"
CACHE_PATH = DATA_DIR / "rewrite_course_descriptions_cache.json"
OUTPUT_PATH = DATA_DIR / "rewrite_course_descriptions_output.json"
TARGET_HEADER = "course_description"
USER_AGENT = "Mozilla/5.0 (compatible; Nyx DGES course-description rewrite/2.0; factual course summaries)"
MAX_CHARS = 2000

BAD_SOURCE_MARKERS = [
    "perfil linkedin", "ciência vitae", "testemunho", "testemunhos", "alumni", "joão pedro",
    "púria esfandiari", "escolha mais acertada", "considero em casa", "decisores no rumo",
    "cookie", "cookies", "javascript", "newsletter", "menu", "404", "not found", "não encontrada",
    "acessibilidade", "mapa do site", "redes sociais", "facebook", "instagram", "linkedin",
    "seminário", "workshop", "job shadowing", "comunidade académica", "auditório", "serviços centrais",
    "decorrerá", "evento", "erasmus", "notícia", "noticias", "news",
    "naric", "suplemento ao diploma", "dges.mctes", "http://", "https://",
    "unidade curricular", "responsável da unidade", "após a frequência", "programa da disciplina",
    "ob1:", "ob2:", "cp1:", "será dada enfâse", "sera dada enfase",
    "engenharia eletrotécnica - sistemas elétricos", "inteligência artificial e engenharia de sistemas",
    "cursos cursos breves", "horários / calendários", "legislação/regulamentos",
    "clínica pedagógica", "provas públicas", "orgãos de gestão", "órgãos de gestão",
    "corpo docente", "guia do estudante", "instalações contactos", "rede o politécnico",
    "observatório", "assinatura e lançamento", "dez 2025", "jan 2026", "fev 2026",
]
STOP_MARKERS = [
    "Plano de estudos", "Plano curricular", "Estrutura curricular", "Unidades curriculares",
    "Candidaturas", "Condições de acesso", "Acesso", "Propinas", "Contactos", "Horário",
    "1º ANO", "1.º ANO", "1 ANO", "Regime", "Calendário", "Documentos", "Mais informação",
    "Testemunhos", "Testemunho", "Alumni", "Perfil LinkedIn", "Perfil Ciência Vitae",
]
GOOD_ANCHORS = [
    "Apresentação", "Apresentacao", "Objetivos", "Objectivos", "Caracterização", "Caracterizacao",
    "O Curso", "Sobre o Curso", "Descrição", "Descricao", "Competências", "Competencias",
    "Saídas Profissionais", "Saidas Profissionais", "Perfil", "Empregabilidade", "Objetivo",
]
GOOD_WORDS = [
    "visa", "pretende", "forma", "prepara", "permite", "desenvolve", "proporciona", "assegura",
    "competências", "competencias", "conhecimentos", "saídas profissionais", "saidas profissionais",
    "perfil", "objetivo", "objectivo", "áreas", "areas", "intervenção", "intervencao",
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


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_progress(payload: dict) -> None:
    payload = dict(payload)
    payload.setdefault("log_path", str(LOG_PATH.resolve()))
    payload.setdefault("cache_path", str(CACHE_PATH.resolve()))
    payload.setdefault("output_path", str(OUTPUT_PATH.resolve()))
    PROGRESS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sh(args: list[str]) -> str:
    return subprocess.check_output(args, text=True)


def gog_base(account: str) -> list[str]:
    return ["gog", "sheets", "--account", account]


def get_sheet(account: str, range_a1: str = "A1:ZZ2000") -> list[list[str]]:
    return json.loads(sh(gog_base(account) + ["get", SHEET_ID, f"{TAB}!{range_a1}", "--json", "--no-input"]))["values"]


def update_range(account: str, a1_range: str, values: list[list[str]]) -> None:
    subprocess.run(
        gog_base(account)
        + [
            "update", SHEET_ID, a1_range,
            "--values-json", json.dumps(values, ensure_ascii=False),
            "--input", "USER_ENTERED", "--no-input",
        ],
        check=True,
    )


def column_letter(index_1_based: int) -> str:
    result = ""
    n = index_1_based
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def clean(value: str) -> str:
    value = html_lib.unescape(value or "")
    value = value.replace("\xa0", " ").replace("\u200b", " ")
    value = re.sub(r"\s+", " ", value).strip(" \t\n\r-–—|•")
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"([.!?]){2,}", r"\1", value)
    return value


def strip_tags(html: str) -> str:
    html = re.sub(r"<(?P<tag>script|style|noscript|svg|nav|footer|header|form|aside)[^>]*>.*?</(?P=tag)>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    html = re.sub(r"<br\s*/?>", ". ", html, flags=re.I)
    html = re.sub(r"</(p|div|li|h[1-6]|td|tr|section|article)>", ". ", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return clean(html)


def strip_tags_plain(html: str) -> str:
    html = re.sub(r"<(?P<tag>script|style|noscript|svg|nav|footer|header|form|aside)[^>]*>.*?</(?P=tag)>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return clean(html)


def fetch(url: str, timeout: int) -> str:
    # Use curl as a subprocess so DNS/TLS stalls are bounded per request even
    # inside worker threads. urllib timeouts are not always enough here.
    proc = subprocess.run(
        [
            "curl", "-L", "--silent", "--show-error", "--max-time", str(timeout),
            "-A", USER_AGENT,
            "-H", "Accept-Language: pt-PT,pt;q=0.9,en;q=0.5",
            url,
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout + 3, check=False,
    )
    if proc.returncode != 0:
        raise TimeoutError(proc.stderr.decode("utf-8", "replace")[:300] or f"curl exit {proc.returncode}")
    data = proc.stdout[:2_500_000]
    if url.lower().endswith(".pdf"):
        raise ValueError("PDF source skipped")
    for enc in ("utf-8", "iso-8859-1", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", "replace")

def threading_is_main() -> bool:
    try:
        import threading
        return threading.current_thread() is threading.main_thread()
    except Exception:
        return False


def dges_field(text: str, label: str, stop_labels: list[str]) -> str:
    pattern = re.escape(label) + r":?\s*(.*?)\s*(?=" + "|".join(re.escape(s) + r":?" for s in stop_labels) + r"|$)"
    m = re.search(pattern, text, flags=re.S | re.I)
    return clean(m.group(1)) if m else ""


def parse_dges_meta(html: str) -> dict[str, str]:
    text = strip_tags_plain(html)
    area = dges_field(text, "Área CNAEF", ["Duração", "ECTS", "Tipo de Ensino", "Concurso"])
    area = re.sub(r"^\d+\s+", "", area).strip()
    return {
        "area": area,
        "duration": dges_field(text, "Duração", ["ECTS", "Tipo de Ensino", "Concurso"]),
        "ects": dges_field(text, "ECTS", ["Tipo de Ensino", "Concurso", "Vagas"]),
        "teaching_type": dges_field(text, "Tipo de Ensino", ["Concurso", "Vagas", "Provas de Ingresso"]),
        "vacancies": dges_field(text, "Vagas para 2026-2027", ["Pré-Requisitos", "Provas de Ingresso", "Classificações Mínimas"]),
    }


def row_value(row: list[str], idx: dict[str, int], header: str) -> str:
    i = idx.get(header)
    if i is None or len(row) <= i:
        return ""
    return clean(row[i])


def degree_label(cycle: str, course_name: str) -> str:
    c = cycle.casefold()
    if "mestrado integrado" in c and "prep" not in c:
        return f"Mestrado Integrado em {course_name}"
    if "prep" in c:
        return f"Preparação para Mestrado Integrado em {course_name}"
    return f"Licenciatura em {course_name}"


def short_institution(row: list[str], idx: dict[str, int]) -> str:
    inst = row_value(row, idx, "institution_name")
    sigla = row_value(row, idx, "institution_sigla")
    parent = row_value(row, idx, "parent_institution_name")
    parent_acr = row_value(row, idx, "parent_institution_acronym")
    if sigla and sigla not in inst:
        inst_part = f"{inst} ({sigla})"
    else:
        inst_part = inst
    if parent_acr and parent_acr not in inst_part:
        return f"{inst_part} / {parent_acr}"
    if parent and parent not in inst_part and len(parent) <= 70:
        return f"{inst_part} / {parent}"
    return inst_part


def markdown_escape_soft(text: str) -> str:
    # Keep normal punctuation; only remove accidental markdown tables/lists leftovers.
    return re.sub(r"\s*\|\s*", ", ", text).strip()


def sentence_split(text: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+", clean(text))
    out = []
    for p in pieces:
        p = clean(p)
        if 90 <= len(p) <= 420:
            out.append(p)
    return out


def reject_sentence(s: str) -> bool:
    low = s.casefold()
    if any(bad in low for bad in BAD_SOURCE_MARKERS):
        return True
    if re.search(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-zà-ÿ]+\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-zà-ÿ]+\s+-\s+Perfil\b", s):
        return True
    if len(re.findall(r"\.", s)) > 8:
        return True
    if sum(ch.isdigit() for ch in s) > len(s) * 0.25:
        return True
    if re.search(r"\b(1[º.ª]?|2[º.ª]?|3[º.ª]?)\s*ANO\b", s, re.I):
        return True
    if re.search(r"\b(OB|CP)\d+\s*[-:]", s, re.I):
        return True
    if re.search(r"\b(Álgebra|Cálculo|Física|Química|Semestre|ECTS)\b.*\b(Álgebra|Cálculo|Física|Química|Semestre|ECTS)\b", s):
        return True
    if re.search(r"\b\d{1,2}\s+de\s+(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b", low):
        return True
    if re.search(r"\b(onde|de|para|com|em)\.$", low):
        return True
    if s.endswith(":") or s.endswith(":."):
        return True
    return False


def trim_at_stop(text: str) -> str:
    positions = []
    low = text.casefold()
    for marker in STOP_MARKERS:
        pos = low.find(marker.casefold())
        if pos > 80:
            positions.append(pos)
    if positions:
        text = text[: min(positions)]
    return clean(text)


def score_sentence(s: str, course_name: str) -> int:
    low = s.casefold()
    score = 0
    tokens = [t.casefold() for t in re.findall(r"[A-Za-zÀ-ÿ]{5,}", course_name)[:5]]
    score += sum(2 for t in tokens if t in low)
    score += sum(2 for w in GOOD_WORDS if w in low)
    if 90 <= len(s) <= 260:
        score += 2
    if any(b in low for b in BAD_SOURCE_MARKERS):
        score -= 20
    if any(w in low for w in ["plano", "propina", "candidatura", "regulamento", "horário"]):
        score -= 2
    return score


def extract_source_sentences(html: str, course_name: str) -> list[str]:
    text = strip_tags(html)
    if not text:
        return []
    # Do not trim the full page at the first administrative marker: many sites
    # put navigation/plano links before the useful presentation/profile text.
    # Trim only the local chunk after each useful anchor.
    anchors: list[int] = []
    for needle in GOOD_ANCHORS + [course_name]:
        if not needle:
            continue
        start = 0
        while True:
            pos = text.casefold().find(needle.casefold(), start)
            if pos < 0:
                break
            anchors.append(pos)
            start = pos + len(needle)
            if len(anchors) > 18:
                break
    candidates: list[str] = []
    if anchors:
        for pos in sorted(set(anchors))[:14]:
            chunk = trim_at_stop(text[pos: pos + 1800])
            candidates.extend(sentence_split(chunk))
    # Meta tags often carry concise factual summaries.
    for m in re.finditer(r"<meta[^>]+(?:name|property)=[\"'](?:description|og:description|twitter:description)[\"'][^>]+content=[\"'](.*?)[\"']", html, flags=re.S | re.I):
        candidates.extend(sentence_split(clean(m.group(1))))
    seen = set()
    usable = []
    course_tokens = [t.casefold() for t in re.findall(r"[A-Za-zÀ-ÿ]{5,}", course_name)[:6]]
    for s in candidates:
        s = markdown_escape_soft(s)
        low = s.casefold()
        key = re.sub(r"\W+", "", low)[:120]
        if key in seen or reject_sentence(s):
            continue
        seen.add(key)
        score = score_sentence(s, course_name)
        has_course_token = any(t in low for t in course_tokens)
        if has_course_token and score >= 2:
            usable.append(s)
        elif score >= 7:
            usable.append(s)
    usable.sort(key=lambda s: score_sentence(s, course_name), reverse=True)
    return usable[:5]


def parse_json_cell(value: str):
    try:
        return json.loads(value) if value else None
    except Exception:
        return None


def best_recent_score(value: str) -> str:
    data = parse_json_cell(value)
    if not isinstance(data, dict) or not data:
        return ""
    years = sorted([y for y in data if re.fullmatch(r"\d{4}", y)], reverse=True)
    if not years:
        return ""
    y = years[0]
    rounds = data.get(y) or {}
    if not isinstance(rounds, dict):
        return ""
    vals = [v for k, v in rounds.items() if v not in (None, "")]
    if not vals:
        return ""
    return f"Em {y}, a nota do último colocado registada foi {', '.join(f'{k}: {v}' for k, v in rounds.items() if v not in (None, ''))}."


def fallback_profile(course_name: str, area: str = "") -> str:
    """Short factual field-level profile derived from the course title/area.

    This is used only when institutional presentation text is unavailable or
    rejected as noisy. It avoids institution-specific claims and sticks to the
    academic/professional domain implied by the course name.
    """
    name = clean(course_name)
    low = name.casefold()
    patterns = [
        (["engenharia informática", "ciência de computadores", "informática", "computação", "software"], "centra-se em programação, algoritmos, sistemas computacionais, dados e desenvolvimento de soluções digitais, combinando fundamentos científicos com aplicação prática em software e tecnologias de informação"),
        (["inteligência artificial", "ciência de dados", "data science", "dados"], "aborda métodos de análise de dados, modelos computacionais, estatística, programação e apoio à decisão, com ligação a aplicações digitais e sistemas inteligentes"),
        (["engenharia mecânica", "mecânica"], "abrange mecânica, materiais, energia, fabrico, projeto e análise de sistemas e equipamentos, preparando para problemas técnicos ligados à indústria e à tecnologia"),
        (["engenharia eletrotécnica", "eletrotécnica", "eletrónica", "automação", "telecomunicações"], "incide sobre eletricidade, eletrónica, automação, sistemas e tecnologias de comunicação, articulando bases de engenharia com projeto, operação e manutenção de soluções técnicas"),
        (["engenharia civil", "construção civil"], "trabalha temas ligados a estruturas, construção, materiais, hidráulica, geotecnia, planeamento e gestão de obras e infraestruturas"),
        (["engenharia química", "química"], "explora princípios de química, processos, materiais, análise laboratorial e transformação industrial, ligando ciência de base a aplicações técnicas"),
        (["bioquímica", "biotecnologia", "biologia", "ciências biomédicas"], "foca o estudo dos sistemas vivos, processos biológicos e métodos laboratoriais, com aplicação em saúde, ambiente, investigação ou produção biotecnológica"),
        (["enfermagem"], "prepara para cuidados de enfermagem, promoção da saúde, prevenção da doença e intervenção junto de pessoas, famílias e comunidades em diferentes contextos clínicos"),
        (["medicina"], "organiza formação científica e clínica orientada para compreensão da saúde e da doença, diagnóstico, terapêutica e prática médica supervisionada"),
        (["farmácia", "ciências farmacêuticas"], "aborda medicamentos, produtos de saúde, análises, farmacologia e uso seguro de terapêuticas em contexto comunitário, hospitalar, laboratorial ou industrial"),
        (["psicologia"], "estuda comportamento, cognição, desenvolvimento e processos psicológicos, integrando métodos científicos e intervenção em contextos humanos e sociais"),
        (["educação", "ensino", "educação básica"], "centra-se em processos de aprendizagem, desenvolvimento, pedagogia e intervenção educativa, articulando fundamentos teóricos com práticas em contextos escolares e comunitários"),
        (["serviço social", "trabalho social"], "aborda intervenção social, políticas sociais, direitos, inclusão e apoio a pessoas, grupos e comunidades em situações de vulnerabilidade ou mudança social"),
        (["gestão", "administração", "management"], "trata organização, estratégia, operações, recursos humanos, marketing, finanças e apoio à decisão em empresas, instituições públicas ou organizações sociais"),
        (["economia"], "estuda produção, consumo, mercados, políticas públicas, finanças e comportamento económico, recorrendo a métodos quantitativos e análise institucional"),
        (["finanças", "contabilidade", "banca", "fiscalidade"], "incide sobre informação financeira, contabilidade, investimento, fiscalidade, banca, seguros e controlo de gestão, com aplicação à decisão económica"),
        (["marketing", "publicidade", "comunicação"], "trabalha comunicação, públicos, marcas, media, conteúdos e estratégias de relação com mercados ou comunidades"),
        (["jornalismo"], "foca recolha, verificação, produção e edição de informação jornalística, com atenção a ética, linguagem, media e contextos sociais"),
        (["direito", "solicitadoria", "criminologia"], "desenvolve formação em normas jurídicas, instituições, procedimentos, direitos e deveres, com aplicação a contextos públicos, privados ou judiciais"),
        (["relações internacionais", "ciência política", "administração pública"], "aborda instituições, políticas públicas, governação, relações entre Estados e organizações, análise social e funcionamento da administração"),
        (["línguas", "tradução", "literatura"], "desenvolve competências linguísticas, culturais e textuais, com ligação a comunicação, tradução, mediação intercultural, ensino ou estudos literários"),
        (["história", "arqueologia", "património"], "estuda sociedades, culturas, documentos, património e processos históricos, recorrendo a métodos de análise crítica e investigação em humanidades"),
        (["filosofia"], "trabalha problemas, conceitos e argumentos sobre conhecimento, ética, linguagem, política, ciência e cultura, valorizando leitura crítica e raciocínio rigoroso"),
        (["design", "multimédia", "artes visuais", "belas-artes"], "combina cultura visual, projeto, criação, comunicação e tecnologias de representação, com aplicação em objetos, imagens, interfaces, media ou experiências"),
        (["arquitetura", "urbanismo"], "articula projeto, desenho, construção, história, território e sustentabilidade na conceção de edifícios, espaços urbanos e ambientes habitados"),
        (["música", "teatro", "dança", "artes performativas"], "desenvolve competências artísticas, técnicas e críticas ligadas à criação, interpretação, composição, performance e enquadramento cultural"),
        (["turismo", "hotelaria", "restauração"], "aborda gestão e operação de serviços turísticos, hospitalidade, destinos, eventos, cultura, património e relação com visitantes"),
        (["desporto", "atividade física"], "estuda movimento humano, treino, saúde, pedagogia, rendimento e gestão de atividades físicas e desportivas"),
        (["agronomia", "agricultura", "zootecnia", "florestal", "ambiente", "recursos naturais"], "integra ciências naturais, produção, sustentabilidade, gestão de recursos e intervenção técnica em sistemas agrícolas, florestais, ambientais ou alimentares"),
        (["matemática", "estatística"], "desenvolve raciocínio abstrato, modelação, análise quantitativa e métodos formais aplicáveis a ciência, tecnologia, economia e investigação"),
        (["física", "geologia", "ciências do oceano"], "explora fenómenos naturais, métodos experimentais, modelação e análise científica, com ligação a investigação, tecnologia, ambiente ou recursos naturais"),
    ]
    for keys, text in patterns:
        if any(k in low for k in keys):
            return f"Enquanto formação em **{name}**, o curso {text}."
    if area and "desconhecido" not in area.casefold():
        return f"Enquanto formação em **{name}**, o curso enquadra conteúdos e práticas associados a **{area}**, articulando conhecimento de base com aplicação em contextos académicos e profissionais dessa área."
    return f"Enquanto formação em **{name}**, o curso organiza-se em torno dos conceitos, métodos e práticas próprios desta área, articulando conhecimento de base com aplicação em contextos académicos e profissionais relacionados."


def build_description(row: list[str], idx: dict[str, int], cache: dict, timeout: int) -> dict:
    course_code = row_value(row, idx, "course_code")
    inst_code = row_value(row, idx, "institution_code")
    cache_key = f"{inst_code}::{course_code}"
    cached = cache.setdefault("results", {}).get(cache_key)
    if cached:
        return cached

    course_name = row_value(row, idx, "course_name")
    cycle = row_value(row, idx, "cycle")
    details_url = row_value(row, idx, "detalhes_do_curso")
    course_url = row_value(row, idx, "course_url")
    inst = short_institution(row, idx)
    city = row_value(row, idx, "cidade")
    district = row_value(row, idx, "distrito")
    meta: dict[str, str] = {}
    source_sentences: list[str] = []
    sources: list[str] = []
    errors: list[str] = []

    # DGES detail first for stable metadata.
    if details_url:
        try:
            html = fetch(details_url, timeout=timeout)
            meta = parse_dges_meta(html)
            sources.append(details_url)
        except Exception as exc:
            errors.append(f"dges={type(exc).__name__}:{exc}")

    # Institution page first for actual presentation text.
    if course_url and course_url.lower().startswith(("http://", "https://")):
        try:
            html = fetch(course_url, timeout=timeout)
            source_sentences.extend(extract_source_sentences(html, course_name))
            sources.append(course_url)
        except Exception as exc:
            errors.append(f"course_url={type(exc).__name__}:{exc}")

    degree = degree_label(cycle, course_name)
    bits = [f"A **{degree}**"]
    if inst:
        prep = "do" if inst.startswith("Instituto") else "da"
        bits.append(f"{prep} **{inst}**")
    opener = " ".join(bits)
    tail = []
    if meta.get("area") and "desconhecido" not in meta.get("area", "").casefold():
        tail.append(f"enquadra-se na área de **{meta['area']}**")
    if city:
        loc = city if not district or district == city else f"{city}, distrito de {district}"
        tail.append(f"é lecionada em **{loc}**")
    if tail:
        opener += " " + " e ".join(tail)
    opener += "."

    details = []
    if meta.get("duration") and meta.get("ects"):
        details.append(f"tem duração de **{meta['duration'].lower()}** e **{meta['ects']} ECTS**")
    elif meta.get("duration"):
        details.append(f"tem duração de **{meta['duration'].lower()}**")
    elif meta.get("ects"):
        details.append(f"tem **{meta['ects']} ECTS**")
    if meta.get("teaching_type"):
        details.append(f"integra o **{meta['teaching_type'].lower()}**")
    if meta.get("vacancies"):
        details.append(f"tem **{meta['vacancies']} vagas** indicadas para 2026-2027")
    details_sentence = ""
    if details:
        details_sentence = "O curso " + ", ".join(details) + "."

    selected = []
    used = set()
    for s in source_sentences:
        # Avoid repeating administrative facts already in details.
        low = s.casefold()
        if any(x in low for x in ["duração", "ects", "vagas", "propinas"]):
            continue
        norm = re.sub(r"\W+", "", low)
        if any(norm and (norm in prev or prev in norm) for prev in used):
            continue
        used.add(norm)
        selected.append(s)
        if sum(len(x) for x in selected) > 650 or len(selected) >= 2:
            break

    paragraphs = [opener]
    if selected:
        paragraphs.append(" ".join(selected))
    else:
        paragraphs.append(fallback_profile(course_name, meta.get("area", "")))
    if details_sentence:
        paragraphs.append(details_sentence)

    desc = "\n\n".join(clean(p) for p in paragraphs if clean(p))
    desc = re.sub(r"\bSegundo\b[^.]*\.", "", desc, flags=re.I)
    desc = clean_markdown(desc)
    if len(desc) > MAX_CHARS:
        desc = trim_to_chars(desc, MAX_CHARS)
    result = {
        "description": desc,
        "sources": sources,
        "errors": errors,
        "chars": len(desc),
        "has_institution_text": bool(selected),
        "updatedAt": now_lisbon(),
    }
    cache["results"][cache_key] = result
    return result


def clean_markdown(desc: str) -> str:
    paragraphs = []
    for part in re.split(r"\n\s*\n", desc):
        part = clean(part)
        if part:
            paragraphs.append(part)
    desc = "\n\n".join(paragraphs)
    desc = re.sub(r"\n{3,}", "\n\n", desc)
    desc = re.sub(r"\*{3,}", "**", desc)
    return desc.strip()


def trim_to_chars(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - 1]
    parts = re.split(r"(?<=[.!?])\s+", cut)
    if len(parts) > 1:
        out = " ".join(parts[:-1]).strip()
        if len(out) >= 300:
            return out
    return cut.rsplit(" ", 1)[0].strip() + "."


def contiguous_groups(pending: dict[int, str], max_rows: int = 100) -> list[tuple[int, int, list[list[str]]]]:
    """Return contiguous row groups small enough for gog's CLI argv limits."""
    groups = []
    current_start = None
    current_values: list[list[str]] = []
    last_row = None
    for sheet_row in sorted(pending):
        should_split = (
            current_start is None
            or last_row is None
            or sheet_row != last_row + 1
            or len(current_values) >= max_rows
        )
        if should_split:
            if current_start is not None and last_row is not None:
                groups.append((current_start, last_row, current_values))
            current_start = sheet_row
            current_values = []
        current_values.append([pending[sheet_row]])
        last_row = sheet_row
    if current_start is not None and last_row is not None:
        groups.append((current_start, last_row, current_values))
    return groups


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=os.environ.get("GOG_ACCOUNT", DEFAULT_ACCOUNT))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0, help="0-based offset in data rows, after header")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true", help="actually write to Google Sheets")
    parser.add_argument("--flush-every", type=int, default=120)
    parser.add_argument("--ignore-cache", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    LOG_PATH.write_text("", encoding="utf-8")
    log(f"starting rewrite :: dry_run={args.dry_run} write={args.write} workers={args.workers}")
    values = get_sheet(args.account)
    headers = values[0]
    idx = {header: i for i, header in enumerate(headers)}
    required = ["course_code", "course_name", "institution_code", "institution_name", "cycle", "detalhes_do_curso", "course_url", TARGET_HEADER]
    missing = [h for h in required if h not in idx]
    if missing:
        raise SystemExit(f"Missing required columns: {', '.join(missing)}")
    desc_col_letter = column_letter(idx[TARGET_HEADER] + 1)

    all_rows = list(enumerate(values[1:], start=2))
    if args.offset:
        all_rows = all_rows[args.offset:]
    if args.limit:
        all_rows = all_rows[: args.limit]
    cache = {"results": {}} if args.ignore_cache else load_json(CACHE_PATH, {"results": {}})
    counters = {"processed": 0, "prepared": 0, "errors": 0, "with_institution_text": 0, "written": 0}
    results: dict[int, str] = {}
    details: dict[int, dict] = {}
    save_progress({"status": "running", "total": len(all_rows), **counters, "startedAt": now_lisbon(), "log_path": str(LOG_PATH.resolve())})

    def work(item):
        sheet_row, row = item
        try:
            res = build_description(row, idx, cache, args.timeout)
            return sheet_row, row_value(row, idx, "course_code"), row_value(row, idx, "course_name"), res, None
        except Exception as exc:
            return sheet_row, row_value(row, idx, "course_code"), row_value(row, idx, "course_name"), None, repr(exc)

    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(work, item) for item in all_rows]
        for n, fut in enumerate(cf.as_completed(futs), start=1):
            sheet_row, code, name, res, err = fut.result()
            counters["processed"] += 1
            if err or not res:
                counters["errors"] += 1
                log(f"[{n}/{len(all_rows)}] row {sheet_row} {code} {name} ERROR {err}")
                continue
            desc = res.get("description", "")
            if not desc or len(desc) > MAX_CHARS or "Segundo a ficha" in desc:
                counters["errors"] += 1
                log(f"[{n}/{len(all_rows)}] row {sheet_row} {code} {name} INVALID chars={len(desc)}")
                continue
            results[sheet_row] = desc
            details[sheet_row] = res
            counters["prepared"] += 1
            if res.get("has_institution_text"):
                counters["with_institution_text"] += 1
            if n % 25 == 0 or n == len(all_rows):
                # Do not serialize the shared cache while workers are mutating it.
                # The cache is safely persisted after the executor finishes.
                save_json(OUTPUT_PATH, {"descriptions": results, "details": details})
                save_progress({"status": "running", "total": len(all_rows), "remaining": len(all_rows) - n, **counters, "updatedAt": now_lisbon()})
            log(f"[{n}/{len(all_rows)}] row {sheet_row} {code} prepared chars={len(desc)} inst_text={res.get('has_institution_text')} sources={len(res.get('sources', []))}")

    save_json(CACHE_PATH, cache)
    save_json(OUTPUT_PATH, {"descriptions": results, "details": details})

    if args.write:
        log(f"writing {len(results)} descriptions to sheet column {desc_col_letter}")
        for start, end, vals in contiguous_groups(results):
            rng = f"{TAB}!{desc_col_letter}{start}:{desc_col_letter}{end}"
            update_range(args.account, rng, vals)
            counters["written"] += len(vals)
            log(f"updated {rng} ({len(vals)} rows)")
            time.sleep(random.uniform(0.4, 1.0))
    else:
        log("not writing to sheet; pass --write to update Google Sheets")

    status = "completed" if counters["errors"] == 0 else "completed-with-errors"
    if args.dry_run and not args.write:
        status = "completed-dry-run" if counters["errors"] == 0 else "completed-dry-run-with-errors"
    save_progress({"status": status, "total": len(all_rows), "remaining": 0, **counters, "finishedAt": now_lisbon()})
    log("done :: " + " ".join(f"{k}={v}" for k, v in counters.items()))
    return 0 if counters["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
