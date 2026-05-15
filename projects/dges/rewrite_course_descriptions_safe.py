#!/usr/bin/env python3
"""Rewrite DGES course descriptions using only structured sheet metadata.

This avoids publishing scraped fragments from institution pages, which can be
ungrammatical, incomplete, duplicated, or irrelevant. The result is deliberately
conservative: a clear public-facing summary that explains what the course is
about, where it is taught, and the key DGES facts already present in the sheet.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import re
import subprocess
import time
import unicodedata
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

SHEET_ID = "1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E"
TAB = "dges_cursos_2026"
DEFAULT_ACCOUNT = "tiago.carvalho@gmail.com"
DATA_DIR = Path("projects/dges/data")
REPORT_PATH = DATA_DIR / "rewrite_course_descriptions_safe_report.json"
MD_REPORT_PATH = DATA_DIR / "rewrite_course_descriptions_safe_report.md"
META_CACHE_PATH = DATA_DIR / "rewrite_course_descriptions_safe_meta_cache.json"
USER_AGENT = "Mozilla/5.0 (compatible; Nyx DGES safe course descriptions)"


def sh(args: list[str]) -> str:
    return subprocess.check_output(args, text=True)


def gog_base(account: str) -> list[str]:
    return ["gog", "sheets", "--account", account]


def get_sheet(account: str) -> list[list[str]]:
    return json.loads(sh(gog_base(account) + ["get", SHEET_ID, f"{TAB}!A1:Y2000", "--json", "--no-input"]))["values"]


def update_range(account: str, a1_range: str, values: list[list[str]]) -> None:
    subprocess.run(
        gog_base(account)
        + [
            "update",
            SHEET_ID,
            a1_range,
            "--values-json",
            json.dumps(values, ensure_ascii=False),
            "--input",
            "USER_ENTERED",
            "--no-input",
        ],
        check=True,
    )


def col_letter(index_1_based: int) -> str:
    out = ""
    n = index_1_based
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def now_lisbon() -> str:
    return dt.datetime.now(ZoneInfo("Europe/Lisbon")).strftime("%Y-%m-%d %H:%M:%S %Z")


def clean(text: str) -> str:
    text = (text or "").replace("\xa0", " ").replace("\u200b", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([.!?]){2,}", r"\1", text)
    return text


def ascii_fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()


def value(row: list[str], idx: dict[str, int], key: str) -> str:
    i = idx.get(key, -1)
    return row[i].strip() if i >= 0 and i < len(row) and isinstance(row[i], str) else ""


def short_institution(row: list[str], idx: dict[str, int]) -> str:
    inst = value(row, idx, "institution_name")
    sigla = value(row, idx, "institution_sigla")
    parent = value(row, idx, "parent_institution_name")
    parent_acr = value(row, idx, "parent_institution_acronym")
    if sigla and sigla not in inst:
        inst = f"{inst} ({sigla})"
    if parent_acr and parent_acr not in inst:
        inst = f"{inst} / {parent_acr}"
    elif parent and parent not in inst and not parent_acr:
        inst = f"{inst} / {parent}"
    return inst


def degree_label(cycle: str, name: str) -> tuple[str, str, str]:
    low = ascii_fold(cycle + " " + name)
    if "mestrado integrado" in low:
        return "Mestrado Integrado", "O", "lecionado"
    if "mestrado" in low or "2" in cycle:
        return "Mestrado", "O", "lecionado"
    if "licenciatura" in low or "1" in cycle:
        return "Licenciatura", "A", "lecionada"
    return "Curso", "O", "lecionado"


def prep_for_institution(inst: str) -> str:
    low = ascii_fold(inst)
    if low.startswith(("instituto", "iscte")):
        return "do"
    if low.startswith(("universidade", "faculdade", "escola", "academia")):
        return "da"
    return "da"


def city_text(row: list[str], idx: dict[str, int]) -> str:
    city = normalize_place(value(row, idx, "cidade"))
    district = normalize_place(value(row, idx, "distrito"))
    if not city:
        return ""
    if district and ascii_fold(district) != ascii_fold(city):
        return f"{city}, distrito de {district}"
    return city


def normalize_place(text: str) -> str:
    # DGES often title-cases particles as "De/Da/Do". For public copy, keep
    # normal Portuguese place-name casing without touching the rest.
    return re.sub(r"\b(Da|De|Do|Das|Dos)\b", lambda m: m.group(1).lower(), text or "")


def extract_between(desc: str, pattern: str) -> str:
    m = re.search(pattern, desc or "", re.I | re.S)
    return clean(m.group(1)) if m else ""


def extract_area(desc: str) -> str:
    return extract_between(desc, r"enquadra-se na área de \*\*(.*?)\*\*")


def extract_facts(desc: str) -> dict[str, str]:
    facts: dict[str, str] = {}
    m = re.search(r"tem duração de \*\*(.*?)\*\*", desc or "", re.I)
    if m:
        facts["duration"] = clean(m.group(1))
    m = re.search(r"\*\*(\d+) ECTS\*\*", desc or "", re.I)
    if m:
        facts["ects"] = m.group(1)
    m = re.search(r"integra o \*\*(.*?)\*\*", desc or "", re.I)
    if m:
        facts["teaching_type"] = clean(m.group(1))
    m = re.search(r"(?:tem|dispõe de) \*\*(\d+) vagas", desc or "", re.I)
    if m:
        facts["vacancies"] = m.group(1)
    return facts


def strip_tags_plain(html: str) -> str:
    html = re.sub(r"<(?P<tag>script|style|noscript|svg|nav|footer|header|form|aside)[^>]*>.*?</(?P=tag)>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return clean(html)


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


def fetch_dges_meta(url: str, timeout: int = 8) -> dict[str, str]:
    if not url:
        return {}
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-PT,pt;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read(700_000)
    for enc in ("utf-8", "iso-8859-1", "cp1252"):
        try:
            return parse_dges_meta(data.decode(enc))
        except UnicodeDecodeError:
            continue
    return parse_dges_meta(data.decode("utf-8", "replace"))


def load_meta_cache() -> dict[str, dict[str, str]]:
    if META_CACHE_PATH.exists():
        try:
            return json.loads(META_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_meta_cache(cache: dict[str, dict[str, str]]) -> None:
    META_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


PROFILE_RULES: list[tuple[list[str], str, str]] = [
    (["engenharia informatica", "ciencia de computadores", "informatica", "software"], "centra-se em programação, algoritmos, sistemas computacionais, bases de dados, redes e desenvolvimento de software", "Prepara para conceber, implementar e manter soluções digitais, com aplicação em empresas tecnológicas, equipas de produto, consultoria, sistemas de informação ou infraestruturas digitais."),
    (["inteligencia artificial", "ciencia de dados", "data science", "dados"], "trabalha análise de dados, estatística, programação, modelos computacionais e apoio à decisão", "Prepara para transformar dados em conhecimento útil, desenvolver modelos e apoiar produtos, serviços e processos orientados por informação."),
    (["engenharia mecanica", "mecanica"], "abrange mecânica, materiais, energia, fabrico, projeto e análise de sistemas e equipamentos", "Prepara para resolver problemas técnicos ligados à indústria, produção, manutenção, desenvolvimento de produto, energia e tecnologia."),
    (["engenharia eletrotecnica", "eletronica", "automacao", "telecomunicacoes", "redes"], "incide sobre eletricidade, eletrónica, automação, sistemas digitais e tecnologias de comunicação", "Prepara para projetar, operar e manter soluções técnicas em energia, controlo, telecomunicações, redes, equipamentos e sistemas industriais."),
    (["engenharia civil", "construcao"], "trabalha estruturas, construção, materiais, hidráulica, geotecnia, planeamento e gestão de obras e infraestruturas", "Prepara para intervir em projeto, acompanhamento, execução e gestão técnica de edifícios, obras públicas e infraestruturas."),
    (["engenharia quimica", "quimica", "processos quimicos"], "explora química, processos, materiais, análise laboratorial e transformação industrial", "Prepara para atuar em laboratórios, indústria, controlo de qualidade, desenvolvimento de processos e áreas técnicas ligadas a materiais, energia, ambiente ou saúde."),
    (["bioquimica", "biotecnologia", "biologia", "biomedica", "bioinformatica"], "foca sistemas vivos, processos biológicos, métodos laboratoriais e tecnologias aplicadas às ciências da vida", "Prepara para contextos de investigação, laboratório, saúde, ambiente, indústria alimentar, biotecnologia ou desenvolvimento de soluções baseadas em conhecimento biológico."),
    (["enfermagem veterinaria", "medicina veterinaria", "veterinaria"], "articula saúde animal, cuidados clínicos, produção, bem-estar, higiene e apoio técnico-veterinário", "Prepara para trabalhar com animais de companhia, produção animal, clínicas, explorações, laboratórios, saúde pública veterinária ou serviços técnicos especializados."),
    (["enfermagem"], "prepara para cuidados de enfermagem, promoção da saúde, prevenção da doença e intervenção junto de pessoas, famílias e comunidades", "Integra formação científica, técnica, ética e relacional para atuação em diferentes contextos clínicos e comunitários."),
    (["medicina"], "organiza formação científica e clínica orientada para compreender saúde, doença, diagnóstico, terapêutica e prática médica supervisionada", "Prepara para uma progressão exigente entre bases biomédicas, contacto clínico, decisão médica e responsabilidade profissional."),
    (["farmacia", "ciencias farmaceuticas"], "aborda medicamentos, produtos de saúde, análises, farmacologia e uso seguro de terapêuticas", "Prepara para contextos comunitários, hospitalares, laboratoriais, regulamentares ou industriais ligados ao medicamento e à saúde."),
    (["nutricao", "dietetica"], "trabalha alimentação, nutrição humana, saúde pública, avaliação nutricional e intervenção alimentar", "Prepara para promover saúde e qualidade de vida em contextos clínicos, comunitários, desportivos, alimentares ou de investigação aplicada."),
    (["psicologia"], "estuda comportamento, cognição, desenvolvimento, emoções e processos psicológicos", "Prepara para compreender pessoas e grupos com base científica, abrindo caminho a intervenção, investigação e especialização em diferentes contextos humanos e sociais."),
    (["servico social", "educacao social", "trabalho social", "animacao sociocultural", "animacao socioeducativa", "gerontologia"], "aborda intervenção social, inclusão, políticas sociais, educação não formal e apoio a pessoas, grupos e comunidades", "Prepara para atuar em instituições sociais, autarquias, projetos comunitários, equipamentos educativos, respostas de apoio e contextos de vulnerabilidade ou mudança social."),
    (["educacao basica", "ensino", "educacao", "pedagogia"], "centra-se em aprendizagem, desenvolvimento, pedagogia, didática e intervenção educativa", "Prepara para trabalhar em contextos escolares, educativos e comunitários, ou para prosseguir formação necessária ao exercício profissional docente quando aplicável."),
    (["gestao turistica", "turismo", "hotelaria", "restauracao", "eventos", "animacao turistica"], "aborda gestão de serviços, destinos, hospitalidade, eventos, património, cultura e relação com visitantes", "Prepara para planear, comunicar, organizar e gerir experiências, operações e projetos em turismo, hotelaria, lazer, cultura ou eventos."),
    (["gestao", "administracao", "management", "recursos humanos", "logistica", "comercial", "negocios"], "trata organização, estratégia, operações, recursos humanos, marketing, finanças e apoio à decisão", "Prepara para compreender o funcionamento de empresas e instituições, analisar problemas de gestão e participar em equipas, projetos e processos de decisão."),
    (["economia"], "estuda produção, consumo, mercados, políticas públicas, finanças e comportamento económico", "Prepara para analisar dados, interpretar contextos económicos e apoiar decisões em empresas, administração pública, consultoria, banca, investigação ou organizações sociais."),
    (["contabilidade", "financas", "fiscalidade", "banca"], "incide sobre informação financeira, contabilidade, investimento, fiscalidade, auditoria, banca, seguros e controlo de gestão", "Prepara para produzir, interpretar e usar informação económica e financeira em empresas, gabinetes, instituições públicas ou entidades reguladas."),
    (["multimedia", "audiovisual", "fotografia", "imagem animada", "arte multimedia", "jogos digitais"], "combina comunicação, imagem, som, vídeo, interação, narrativa digital e tecnologias de produção multimédia", "Prepara para conceber e produzir conteúdos, interfaces, aplicações, experiências interativas e produtos audiovisuais para plataformas digitais e contextos criativos."),
    (["marketing", "publicidade", "relacoes publicas", "comunicacao empresarial", "comunicacao organizacional"], "trabalha públicos, marcas, comunicação estratégica, conteúdos, mercados e relação com comunidades", "Prepara para planear campanhas, gerir presença digital, analisar públicos e apoiar a comunicação de empresas, instituições, produtos ou causas."),
    (["jornalismo", "ciencias da comunicacao", "comunicacao social", "media"], "foca comunicação, media, produção de informação, escrita, edição, ética e leitura crítica da sociedade", "Prepara para criar, verificar e distribuir conteúdos em ambientes jornalísticos, institucionais, digitais, audiovisuais ou multiplataforma."),
    (["design", "artes plasticas", "belas-artes", "artes visuais"], "combina cultura visual, projeto, criação, comunicação e tecnologias de representação", "Prepara para desenvolver soluções visuais, objetos, interfaces, espaços, imagens ou experiências, articulando criatividade, método de projeto e domínio técnico."),
    (["arquitetura", "urbanismo"], "articula projeto, desenho, construção, história, território e sustentabilidade", "Prepara para pensar e conceber edifícios, espaços urbanos e ambientes habitados, combinando cultura arquitetónica, técnica e responsabilidade social."),
    (["musica", "teatro", "danca", "artes performativas", "espetaculo"], "desenvolve competências artísticas, técnicas e críticas ligadas à criação, interpretação, composição, produção e performance", "Prepara para intervir em projetos culturais e criativos, com domínio prático, enquadramento histórico e capacidade de criação colaborativa."),
    (["direito", "solicitadoria", "criminologia"], "desenvolve formação em normas jurídicas, instituições, procedimentos, direitos e deveres", "Prepara para interpretar problemas legais, apoiar processos, compreender sistemas de justiça e atuar em contextos públicos, privados ou judiciais."),
    (["relacoes internacionais", "ciencia politica", "administracao publica", "estudos europeus"], "aborda instituições, políticas públicas, governação, relações internacionais, administração e análise social", "Prepara para compreender decisões públicas, organizações, sistemas políticos e contextos nacionais ou internacionais."),
    (["linguas", "traducao", "literatura", "linguagem", "linguistica", "lingua gestual"], "desenvolve competências linguísticas, culturais, textuais e de comunicação", "Prepara para trabalhar com línguas, textos, tradução, mediação cultural, ensino, comunicação, revisão, interpretação ou estudos literários e linguísticos."),
    (["historia", "arqueologia", "patrimonio"], "estuda sociedades, culturas, documentos, património e processos históricos", "Prepara para analisar fontes, interpretar contextos e intervir em investigação, cultura, educação, museus, património ou comunicação histórica."),
    (["filosofia"], "trabalha problemas, conceitos e argumentos sobre conhecimento, ética, linguagem, política, ciência e cultura", "Prepara para leitura crítica, escrita rigorosa, debate fundamentado e análise conceptual em contextos culturais, educativos, sociais ou profissionais."),
    (["desporto", "atividade fisica"], "estuda movimento humano, treino, saúde, pedagogia, rendimento e gestão de atividades físicas e desportivas", "Prepara para planear, acompanhar e avaliar práticas desportivas, programas de exercício, projetos educativos ou atividades ligadas ao bem-estar e ao rendimento."),
    (["agronom", "agricultura", "zootecnia", "florest", "ambiente", "recursos naturais", "enologia", "alimentar"], "integra ciências naturais, produção, sustentabilidade, gestão de recursos e intervenção técnica", "Prepara para atuar em sistemas agrícolas, florestais, ambientais, alimentares ou vitivinícolas, combinando conhecimento científico com aplicação no terreno e em organizações."),
    (["matematica", "estatistica"], "desenvolve raciocínio abstrato, modelação, análise quantitativa e métodos formais", "Prepara para resolver problemas complexos em ciência, tecnologia, economia, ensino, investigação, dados ou apoio à decisão."),
    (["fisica", "geologia", "oceano", "ambiente"], "explora fenómenos naturais, métodos experimentais, modelação e análise científica", "Prepara para investigação, tecnologia, ambiente, recursos naturais, monitorização, ensino ou aplicações científicas em contexto profissional."),
    (["documentacao", "informacao", "biblioteconomia", "arquivo"], "trabalha organização, preservação, recuperação e gestão de informação e documentação", "Prepara para atuar em bibliotecas, arquivos, centros de documentação, serviços digitais, gestão de conteúdos e sistemas de informação."),
]


def profile(course_name: str, area: str) -> tuple[str, str]:
    low = ascii_fold(f"{course_name} {area}")
    for keys, sentence1, sentence2 in PROFILE_RULES:
        if any(k in low for k in keys):
            return sentence1, sentence2
    if area:
        return (
            f"enquadra conteúdos, métodos e práticas associados a {area}",
            "Prepara para compreender a área de forma aplicada, desenvolver competências técnicas e críticas e prosseguir percursos académicos ou profissionais relacionados.",
        )
    return (
        "organiza-se em torno dos conhecimentos, métodos e práticas centrais da área do curso",
        "Prepara para desenvolver competências técnicas, pensamento crítico e capacidade de aplicação em contextos académicos e profissionais relacionados.",
    )


def fact_sentence(facts: dict[str, str]) -> str:
    parts: list[str] = []
    if facts.get("duration") and facts.get("ects"):
        parts.append(f"tem duração de **{facts['duration'].lower()}** e **{facts['ects']} ECTS**")
    elif facts.get("duration"):
        parts.append(f"tem duração de **{facts['duration'].lower()}**")
    elif facts.get("ects"):
        parts.append(f"tem **{facts['ects']} ECTS**")
    if facts.get("teaching_type"):
        parts.append(f"integra o **{facts['teaching_type'].lower()}**")
    if facts.get("vacancies"):
        parts.append(f"dispõe de **{facts['vacancies']} vagas previstas para 2026-2027**")
    if not parts:
        return ""
    return "O curso " + ", ".join(parts) + "."


def build_description(row: list[str], idx: dict[str, int], meta_cache: dict[str, dict[str, str]] | None = None) -> str:
    name = value(row, idx, "course_name")
    old = value(row, idx, "course_description")
    cycle = value(row, idx, "cycle")
    degree, article, taught = degree_label(cycle, name)
    inst = short_institution(row, idx)
    meta_key = f"{value(row, idx, 'institution_code')}::{value(row, idx, 'course_code')}"
    meta = (meta_cache or {}).get(meta_key, {})
    area = extract_area(old) or clean(meta.get("area", ""))
    city = city_text(row, idx)
    facts = extract_facts(old)
    for k in ("duration", "ects", "teaching_type", "vacancies"):
        if not facts.get(k) and meta.get(k):
            facts[k] = clean(str(meta[k]))

    opener = f"{article} **{degree} em {name}**"
    if inst:
        opener += f" {prep_for_institution(inst)} **{inst}**"
    tail: list[str] = []
    if area:
        tail.append(f"enquadra-se na área de **{area}**")
    if city:
        tail.append(f"é {taught} em **{city}**")
    if tail:
        opener += " " + " e ".join(tail)
    opener += "."

    p1, p2 = profile(name, area)
    body = f"Enquanto formação em **{name}**, o curso {p1}. {p2}"

    paragraphs = [opener, body]
    facts_s = fact_sentence(facts)
    if facts_s:
        paragraphs.append(facts_s)
    return "\n\n".join(clean(p) for p in paragraphs if clean(p))


def contiguous_groups(pending: dict[int, str], max_rows: int = 80) -> list[tuple[int, int, list[list[str]]]]:
    groups = []
    start = None
    last = None
    values: list[list[str]] = []
    for row in sorted(pending):
        if start is None or last is None or row != last + 1 or len(values) >= max_rows:
            if start is not None and last is not None:
                groups.append((start, last, values))
            start = row
            values = []
        values.append([pending[row]])
        last = row
    if start is not None and last is not None:
        groups.append((start, last, values))
    return groups


def quality_flags(desc: str) -> list[str]:
    flags = []
    if any(p and re.match(r"^[a-záéíóúâêôãõç]", p.strip()) for p in desc.split("\n\n")):
        flags.append("lowercase_paragraph")
    if re.search(r"\b(objetivos|objectivos),|dota-los|pretende,? também|;\.|,\.|:\.|\b(provas de ingresso|cookies|testemunhos?|linkedin|plano de estudos)\b", desc, re.I):
        flags.append("bad_fragment")
    if re.search(r"\bA \*\*Mestrado\b", desc):
        flags.append("bad_article")
    if any(len(s) > 420 for s in re.split(r"(?<=[.!?])\s+", desc)):
        flags.append("long_sentence")
    if len(desc) > 2000:
        flags.append("too_long")
    return flags


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=DEFAULT_ACCOUNT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    values = get_sheet(args.account)
    headers = values[0]
    idx = {h: i for i, h in enumerate(headers)}
    desc_col = col_letter(idx["course_description"] + 1)

    rows = list(enumerate(values[1:], start=2))
    if args.offset:
        rows = rows[args.offset:]
    if args.limit:
        rows = rows[: args.limit]

    meta_cache = load_meta_cache()
    missing_meta: list[tuple[str, str]] = []
    for _sheet_row, row in rows:
        key = f"{value(row, idx, 'institution_code')}::{value(row, idx, 'course_code')}"
        old = value(row, idx, "course_description")
        needs_meta = "enquadra-se na área de **" not in old or not any(x in old for x in ["ECTS", "vagas", "duração"])
        if needs_meta and key not in meta_cache:
            url = value(row, idx, "detalhes_do_curso")
            if url:
                missing_meta.append((key, url))
    if missing_meta:
        print(f"fetching DGES metadata for {len(missing_meta)} rows", flush=True)
        with cf.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = {pool.submit(fetch_dges_meta, url): key for key, url in missing_meta}
            for n, fut in enumerate(cf.as_completed(futures), start=1):
                key = futures[fut]
                try:
                    meta_cache[key] = fut.result()
                except Exception as exc:
                    meta_cache[key] = {"error": f"{type(exc).__name__}: {exc}"}
                if n % 50 == 0 or n == len(futures):
                    save_meta_cache(meta_cache)
                    print(f"metadata {n}/{len(futures)}", flush=True)
        save_meta_cache(meta_cache)

    pending: dict[int, str] = {}
    report_rows = []
    for sheet_row, row in rows:
        old = value(row, idx, "course_description")
        new = build_description(row, idx, meta_cache)
        flags = quality_flags(new)
        changed = new != old
        if changed:
            pending[sheet_row] = new
        report_rows.append(
            {
                "row": sheet_row,
                "course_code": value(row, idx, "course_code"),
                "course_name": value(row, idx, "course_name"),
                "institution": value(row, idx, "institution_name"),
                "changed": changed,
                "quality_flags_after": flags,
                "old_chars": len(old),
                "new_chars": len(new),
            }
        )

    if args.write:
        for start, end, vals in contiguous_groups(pending):
            rng = f"{TAB}!{desc_col}{start}:{desc_col}{end}"
            update_range(args.account, rng, vals)
            print(f"updated {rng} ({len(vals)} rows)", flush=True)
            time.sleep(0.5)

    remaining_flags = [r for r in report_rows if r["quality_flags_after"]]
    report = {
        "generated": now_lisbon(),
        "write": args.write,
        "rows_reviewed": len(rows),
        "rows_changed": len(pending),
        "remaining_quality_flags": len(remaining_flags),
        "remaining_flag_rows": remaining_flags[:50],
        "rows": report_rows,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    MD_REPORT_PATH.write_text(
        "# Safe course description rewrite report\n\n"
        f"Generated: {report['generated']}\n\n"
        f"- Rows reviewed: {report['rows_reviewed']}\n"
        f"- Rows changed: {report['rows_changed']}\n"
        f"- Remaining quality flags after rewrite: {report['remaining_quality_flags']}\n"
        f"- Write mode: {report['write']}\n",
        encoding="utf-8",
    )
    print(json.dumps({k: report[k] for k in ["rows_reviewed", "rows_changed", "remaining_quality_flags", "write"]}, ensure_ascii=False))
    return 0 if not remaining_flags else 2


if __name__ == "__main__":
    raise SystemExit(main())
