#!/usr/bin/env python3
"""Fill parent_institutions logo_url and photo_url columns in the DGES spreadsheet.

Sources, in order:
- Wikidata P154 (logo image) and P18 (image/photo), converted to Wikimedia Commons file URLs.
- Official website homepage metadata / image tags for rows where Wikidata is missing.

The script updates the Google Sheet in one batch to avoid Sheets API write quota spikes.
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SHEET_ID = "1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E"
ACCOUNT = "tiago.carvalho@gmail.com"
TAB = "parent_institutions"
CACHE_PATH = Path(__file__).with_name("data") / "parent_institution_images_cache.json"
USER_AGENT = "OpenClaw DGES parent institution enrichment/1.0"

# Official homepages used both as a fallback source and to validate likely official images.
OFFICIAL_WEBSITES = {
    "Instituto Politécnico de Viseu": "https://www.ipv.pt/",
    "Instituto Politécnico de Bragança": "https://portal3.ipb.pt/",
    "Instituto Politécnico de Castelo Branco": "https://www.ipcb.pt/",
    "Instituto Politécnico de Portalegre": "https://www.ipportalegre.pt/",
    "Instituto Politécnico de Tomar": "https://portal2.ipt.pt/",
    "Instituto Politécnico do Cávado e do Ave": "https://ipca.pt/",
    "Instituto Politécnico de Lisboa": "https://www.ipl.pt/",
    "Instituto Politécnico da Guarda": "https://politecnicoguarda.pt/",
    "Universidade de Trás-os-Montes e Alto Douro": "https://www.utad.pt/",
    "Universidade do Minho": "https://www.uminho.pt/",
    "Instituto Politécnico de Coimbra": "https://www.ipc.pt/",
    "Instituto Politécnico de Leiria": "https://www.ipleiria.pt/",
    "Instituto Politécnico de Viana do Castelo": "https://www.ipvc.pt/",
    "Universidade de Aveiro": "https://www.ua.pt/",
    "Universidade do Algarve": "https://www.ualg.pt/",
    "Instituto Politécnico do Porto": "https://www.ipp.pt/",
    "ISCTE - Instituto Universitário de Lisboa": "https://www.iscte-iul.pt/",
    "Universidade do Porto": "https://www.up.pt/",
    "Instituto Politécnico de Santarém": "https://www.ipsantarem.pt/",
    "Universidade de Lisboa": "https://www.ulisboa.pt/",
    "Instituto Politécnico de Setúbal": "https://www.ips.pt/",
    "Instituto Politécnico de Beja": "https://www.ipbeja.pt/",
    "Escola Superior Náutica Infante D. Henrique": "https://www.enautica.pt/",
    "Escola Superior de Hotelaria e Turismo do Estoril": "https://www.eshte.pt/",
    "Universidade de Évora": "https://www.uevora.pt/",
    "Universidade de Coimbra": "https://www.uc.pt/",
    "Instituto Universitário Militar": "https://www.ium.pt/",
    "Universidade dos Açores": "https://uac.pt/",
    "Universidade Nova de Lisboa": "https://www.unl.pt/",
    "Universidade da Beira Interior": "https://www.ubi.pt/",
    "Universidade da Madeira": "https://www.uma.pt/",
    "Instituto Superior de Ciências Policiais e Segurança Interna": "https://www.iscpsi.pt/",
}

# A few entities have weak/ambiguous Wikidata search results; pinning avoids wrong matches.
WIKIDATA_QID_OVERRIDES = {
    "Universidade do Porto": "Q1422903",
    "Instituto Politécnico de Viseu": "Q10302641",
    "Instituto Politécnico de Bragança": "Q10302635",
    "Instituto Politécnico de Castelo Branco": "Q10302131",
    "Instituto Politécnico de Portalegre": "Q10302503",
    "Instituto Politécnico de Tomar": "Q29565528",
    "Instituto Politécnico do Cávado e do Ave": "Q10302640",
    "Instituto Politécnico de Lisboa": "Q10302370",
    "Instituto Politécnico da Guarda": "Q10302254",
    "Universidade de Trás-os-Montes e Alto Douro": "Q1549847",
    "Universidade do Minho": "Q1551958",
    "Instituto Politécnico de Coimbra": "Q2103165",
    "Instituto Politécnico de Leiria": "Q7227031",
    "Instituto Politécnico de Viana do Castelo": "Q7227039",
    "Universidade de Aveiro": "Q29671",
    "Universidade do Algarve": "Q1928343",
    "Instituto Politécnico do Porto": "Q4348556",
    "ISCTE - Instituto Universitário de Lisboa": "Q1431066",
    "Instituto Politécnico de Santarém": "Q10302555",
    "Universidade de Lisboa": "Q1552759",
    "Instituto Politécnico de Setúbal": "Q10302572",
    "Instituto Politécnico de Beja": "Q10302085",
    "Escola Superior Náutica Infante D. Henrique": "Q10274375",
    "Escola Superior de Hotelaria e Turismo do Estoril": "Q10274496",
    "Universidade de Évora": "Q1557861",
    "Universidade de Coimbra": "Q368643",
    "Instituto Universitário Militar": "Q24939561",
    "Universidade dos Açores": "Q588147",
    "Universidade Nova de Lisboa": "Q1979891",
    "Universidade da Beira Interior": "Q1955890",
    "Universidade da Madeira": "Q1434847",
    "Instituto Superior de Ciências Policiais e Segurança Interna": "Q6041513",
}

# Prefer vetted official-site URLs where Wikidata is missing/ambiguous or the site uses inline SVG.
MANUAL_IMAGE_OVERRIDES = {
    "Instituto Politécnico de Bragança": {
        "logo_url": "https://portal3.ipb.pt/templates/ipb-template-home/images/logo.png",
        "photo_url": "https://portal3.ipb.pt/images/ipb/banner_geral_IPB_202011.png",
    },
    "Instituto Politécnico de Portalegre": {
        "logo_url": "https://www.ipportalegre.pt/static/ippimages/Logo_upportalegre_cor_header_v2.svg",
        "photo_url": "https://www.ipportalegre.pt/media/filer_public_thumbnails/filer_public/04/d4/04d4eb7f-69ae-4291-bd87-5017279f8ba8/a-escolha-certa-2026_banner.jpg__1920x677_q85_crop-center_subsampling-2.jpg",
    },
    "Instituto Politécnico de Tomar": {
        "logo_url": "https://portal2.ipt.pt/img/logo_v2.png?v=3",
        "photo_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Campus%20do%20IPT%20em%202019.jpg?width=1200",
    },
    "Instituto Politécnico do Cávado e do Ave": {
        "logo_url": "https://ipca.pt/wp-content/uploads/2023/11/ipca_logo_pt.svg",
        "photo_url": "https://ipca.pt/wp-content/uploads/2026/05/1-1-scaled.jpg",
    },
    "Instituto Politécnico de Lisboa": {
        "photo_url": "https://www.ipl.pt/sites/default/files/img_banner_site_0.jpg",
    },
    "Instituto Politécnico de Coimbra": {
        "logo_url": "https://www.ipc.pt/wp-content/uploads/2020/03/svg_logo.svg",
        "photo_url": "https://www.ipc.pt/wp-content/uploads/2021/07/1-300x200-1.jpg",
    },
    "Instituto Politécnico de Leiria": {
        "logo_url": "https://www.ipleiria.pt/wp-content/themes/wp-theme--ipleiria/assets/img/favicon/favicon.svg",
        "photo_url": "https://www.ipleiria.pt/wp-content/uploads/2021/03/politecnico_menu.jpg",
    },
    "Instituto Politécnico de Viana do Castelo": {
        "logo_url": "https://www.ipvc.pt/wp-content/uploads/2026/01/logo_ipvc_svg2-sunrise.svg",
        "photo_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Polytechnic%20Institute%20of%20Viana%20do%20Castelo.jpg?width=1200",
    },
    "Universidade de Aveiro": {
        "logo_url": "https://www.ua.pt/imgs/icons/icon-512x512.png",
        "photo_url": "https://static.ua.pt/images/ua/sm-campus.png",
    },
    "Instituto Politécnico do Porto": {
        "logo_url": "https://www.ipp.pt/logo-ipp.png",
        "photo_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Presid%C3%AAncia%20do%20Polit%C3%A9cnico%20do%20Porto.jpg?width=1200",
    },
    "Instituto Politécnico de Santarém": {
        "photo_url": "https://www.ipsantarem.pt/wp-content/uploads/2026/04/TA9A9961-1-630x420.webp",
    },
    "Instituto Politécnico de Beja": {
        "logo_url": "https://www.ipbeja.pt/PublishingImages/Logo-IPBejaI.png",
        "photo_url": "https://www.ipbeja.pt/PublishingImages/BannerIPBejaSite-2019.jpg",
    },
    "Escola Superior de Hotelaria e Turismo do Estoril": {
        "logo_url": "https://www.eshte.pt/contents/global/logo-site-cabecalho.png",
        "photo_url": "http://www.eshte.pt/contents/sitemetatagsanalytics/share.jpg",
    },
    "Universidade de Évora": {
        "photo_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Universidade%20de%20%C3%89vora%20-%20Claustro%20geral%20dos%20Estudos%20%282%29.jpg?width=1200",
    },
    "Universidade de Coimbra": {
        "logo_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Seal%20of%20the%20University%20of%20Coimbra.svg?width=500",
        "photo_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Coimbra%20December%202011-19a.jpg?width=1200",
    },
    "Instituto Universitário Militar": {
        "photo_url": "https://www.ium.pt/images/website/IUM_400.png",
    },
    "Universidade Nova de Lisboa": {
        "logo_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Universidade%20NOVA%20de%20Lisboa%20logo%20logotipo%202021.png?width=500",
        "photo_url": "https://commons.wikimedia.org/wiki/Special:FilePath/ReitoriaUNL.jpg?width=1200",
    },
    "Universidade da Beira Interior": {
        "photo_url": "https://www.ubi.pt/Ficheiros/SlideShow/492/banner%20vive_1920%20480.jpg",
    },
    "Universidade da Madeira": {
        "logo_url": "https://commons.wikimedia.org/wiki/Special:FilePath/UMa.png?width=500",
        "photo_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Universidade%20da%20Madeira.jpg?width=1200",
    },
    "Instituto Superior de Ciências Policiais e Segurança Interna": {
        "logo_url": "http://www.iscpsi.pt/Style%20Library/iscpsi/images/logoISCPSI.png",
        "photo_url": "https://commons.wikimedia.org/wiki/Special:FilePath/PSP%20INSTITUTO%20SUPERIOR%20DE%20CI%C3%8ANCIAS%20POLICIAIS%20E%20SEGURAN%C3%87A%20INTERNA.png?width=1200",
    },
}


def http_json(url: str, params: dict[str, Any]) -> Any:
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{qs}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_text(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as resp:
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None
            raw = resp.read(700_000)
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")
    except Exception:
        return None


def commons_file_url(filename: str, width: int | None = None) -> str:
    # Special:FilePath is stable and redirects to the current Commons file URL.
    quoted = urllib.parse.quote(filename.replace(" ", "_"), safe="")
    url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{quoted}"
    if width:
        url += f"?width={width}"
    return url


def wikidata_claims(qid: str) -> dict[str, list[str]]:
    data = http_json(
        "https://www.wikidata.org/w/api.php",
        {"action": "wbgetentities", "ids": qid, "props": "claims", "format": "json"},
    )
    entity = data.get("entities", {}).get(qid, {})
    out: dict[str, list[str]] = {}
    for prop in ("P154", "P18"):
        values: list[str] = []
        for claim in entity.get("claims", {}).get(prop, []):
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
            if isinstance(value, str):
                values.append(value)
        out[prop] = values
    return out


def find_best_img_from_site(site_url: str) -> tuple[str, str]:
    text = http_text(site_url)
    if not text:
        return "", ""
    # Metadata images tend to be campus/building/publication thumbnails.
    photo = ""
    for pattern in [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    ]:
        m = re.search(pattern, text, flags=re.I)
        if m:
            photo = urllib.parse.urljoin(site_url, html.unescape(m.group(1).strip()))
            break

    logo = ""
    # Search image tags whose alt/class/src suggests a logo.
    for m in re.finditer(r'<img\b[^>]*>', text, flags=re.I):
        tag = m.group(0)
        lower = tag.lower()
        if not any(k in lower for k in ("logo", "brand", "logotipo")):
            continue
        src_m = re.search(r'\s(?:src|data-src|data-lazy-src)=["\']([^"\']+)["\']', tag, flags=re.I)
        if src_m:
            logo = urllib.parse.urljoin(site_url, html.unescape(src_m.group(1).strip()))
            break

    if photo == logo:
        photo = ""
    return logo, photo


def gog_get(range_: str) -> list[list[str]]:
    cmd = [
        "gog", "sheets", "get", SHEET_ID, range_,
        "--account", ACCOUNT, "--json", "--no-input",
    ]
    raw = subprocess.check_output(cmd, text=True)
    return json.loads(raw).get("values", [])


def gog_update(range_: str, values: list[list[str]]) -> None:
    cmd = [
        "gog", "sheets", "update", SHEET_ID, range_,
        "--account", ACCOUNT,
        "--values-json", json.dumps(values, ensure_ascii=False),
        "--input", "USER_ENTERED", "--no-input",
    ]
    subprocess.run(cmd, check=True)


def load_cache() -> dict[str, Any]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def save_cache(cache: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True))


def resolve_images(name: str) -> dict[str, str]:
    qid = WIKIDATA_QID_OVERRIDES.get(name, "")
    manual = MANUAL_IMAGE_OVERRIDES.get(name, {})
    logo = manual.get("logo_url", "")
    photo = manual.get("photo_url", "")
    source_bits = ["manual:official_site_or_vetted_commons"] if manual else []

    if qid:
        try:
            claims = wikidata_claims(qid)
            if not logo and claims.get("P154"):
                logo = commons_file_url(claims["P154"][0], width=500)
                source_bits.append(f"logo:wikidata:{qid}:P154")
            if not photo and claims.get("P18"):
                photo = commons_file_url(claims["P18"][0], width=1200)
                source_bits.append(f"photo:wikidata:{qid}:P18")
        except Exception as exc:
            source_bits.append(f"wikidata_error:{type(exc).__name__}")

    site = OFFICIAL_WEBSITES.get(name, "")
    if site and (not logo or not photo):
        site_logo, site_photo = find_best_img_from_site(site)
        if not logo and site_logo:
            logo = site_logo
            source_bits.append("logo:official_site")
        if not photo and site_photo and "logo" not in site_photo.lower():
            photo = site_photo
            source_bits.append("photo:official_site_meta")

    return {"logo_url": logo, "photo_url": photo, "qid": qid, "website": site, "source": ";".join(source_bits)}


def main() -> int:
    values = gog_get(f"{TAB}!A1:D200")
    if not values or values[0][:2] != ["parent_institution_name", "parent_institution_acronym"]:
        raise SystemExit("Unexpected parent_institutions headers")

    cache = load_cache()
    output = [["logo_url", "photo_url"]]
    rows = values[1:]
    for idx, row in enumerate(rows, start=2):
        if not row or not row[0].strip():
            continue
        name = row[0].strip()
        existing_logo = row[2].strip() if len(row) > 2 else ""
        existing_photo = row[3].strip() if len(row) > 3 else ""
        if name in MANUAL_IMAGE_OVERRIDES:
            data = resolve_images(name)
            cache[name] = data
            save_cache(cache)
            time.sleep(0.25)
        elif existing_logo and existing_photo:
            data = {"logo_url": existing_logo, "photo_url": existing_photo, "source": "existing"}
        elif name in cache and cache[name].get("logo_url") and cache[name].get("photo_url"):
            data = cache[name]
        else:
            data = resolve_images(name)
            cache[name] = data
            save_cache(cache)
            time.sleep(0.25)
        output.append([data.get("logo_url", ""), data.get("photo_url", "")])
        print(f"row {idx}: {name} -> logo={'yes' if output[-1][0] else 'no'} photo={'yes' if output[-1][1] else 'no'} [{data.get('source','')}]")

    last_row = len(output)
    gog_update(f"{TAB}!C1:D{last_row}", output)
    print(f"Updated {TAB}!C1:D{last_row}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
