#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

FILE_ID = "1_XXcOGVJr5sbynUBou0LAIdw0djQ8bHxkJuuDEDjLBs"
FILE_URL = f"https://docs.google.com/spreadsheets/d/{FILE_ID}/edit"
ACCOUNT = "tiago@pushnews.com.br"
OWNER_EMAIL = "tiago@pushnews.com.br"
CREDENTIALS_PATH = Path("/data/.config/gogcli/credentials.json")
STATE_DIR_DEFAULT = Path("/data/.openclaw/workspace/data/pushnews_sheet_monitor")
STATE_PATH_DEFAULT = STATE_DIR_DEFAULT / "state.json"
SNAPSHOT_PATH_DEFAULT = STATE_DIR_DEFAULT / "latest.xlsx"
NS_MAIN = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
NS_REL = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}


def run_cmd(cmd):
    return subprocess.check_output(cmd, text=True)


def export_refresh_token(account: str) -> str:
    fd, path = tempfile.mkstemp(prefix="gog-token-", suffix=".json")
    os.close(fd)
    os.unlink(path)
    try:
        subprocess.check_call(
            ["gog", "auth", "tokens", "export", account, "--out", path, "--overwrite", "--no-input"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)["refresh_token"]
    finally:
        if os.path.exists(path):
            os.remove(path)


def get_access_token() -> str:
    with open(CREDENTIALS_PATH, "r", encoding="utf-8") as fh:
        creds = json.load(fh)
    app = creds.get("installed") or creds.get("web") or creds
    refresh_token = export_refresh_token(ACCOUNT)
    payload = urllib.parse.urlencode(
        {
            "client_id": app["client_id"],
            "client_secret": app["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=payload)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["access_token"]


def api_get_json(url: str, access_token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def get_revisions() -> list[dict]:
    token = get_access_token()
    url = (
        f"https://www.googleapis.com/drive/v3/files/{FILE_ID}/revisions"
        "?fields=revisions(id,modifiedTime,lastModifyingUser(displayName,emailAddress))"
    )
    data = api_get_json(url, token)
    return data.get("revisions", [])


def export_snapshot(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    subprocess.check_call(
        [
            "gog",
            "sheets",
            "export",
            FILE_ID,
            "--format",
            "xlsx",
            "--out",
            str(out_path),
            "--account",
            ACCOUNT,
            "--no-input",
        ],
        stdout=subprocess.DEVNULL,
    )


def col_to_name(n: int) -> str:
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    strings = []
    for si in root.findall("x:si", NS_MAIN):
        parts = []
        for node in si.iterfind(".//x:t", NS_MAIN):
            parts.append(node.text or "")
        strings.append("".join(parts))
    return strings


def sheet_targets(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("r:Relationship", NS_REL)
    }
    targets = []
    for sheet in wb.findall("x:sheets/x:sheet", NS_MAIN):
        name = sheet.attrib["name"]
        rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        target = rel_map[rel_id]
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        targets.append((name, target))
    return targets


def parse_sheet(zf: zipfile.ZipFile, target: str, shared_strings: list[str]) -> dict[str, str]:
    root = ET.fromstring(zf.read(target))
    cells = {}
    for cell in root.findall(".//x:c", NS_MAIN):
        ref = cell.attrib.get("r")
        if not ref:
            continue
        formula = cell.find("x:f", NS_MAIN)
        value_node = cell.find("x:v", NS_MAIN)
        inline = cell.find("x:is", NS_MAIN)
        cell_type = cell.attrib.get("t")
        if formula is not None:
            formula_text = formula.text or ""
            if value_node is not None and value_node.text not in (None, ""):
                value = f"={formula_text} => {value_node.text}"
            else:
                value = f"={formula_text}"
        elif inline is not None:
            value = "".join(t.text or "" for t in inline.findall(".//x:t", NS_MAIN))
        elif value_node is None:
            value = ""
        else:
            raw = value_node.text or ""
            if cell_type == "s":
                try:
                    value = shared_strings[int(raw)]
                except Exception:
                    value = raw
            elif cell_type == "b":
                value = "TRUE" if raw == "1" else "FALSE"
            else:
                value = raw
        cells[ref] = value
    return cells


def load_workbook_values(path: Path) -> dict[str, dict[str, str]]:
    with zipfile.ZipFile(path, "r") as zf:
        shared_strings = load_shared_strings(zf)
        result = {}
        for sheet_name, target in sheet_targets(zf):
            result[sheet_name] = parse_sheet(zf, target, shared_strings)
        return result


def diff_workbooks(old_path: Path, new_path: Path) -> dict:
    old = load_workbook_values(old_path) if old_path.exists() else {}
    new = load_workbook_values(new_path)
    per_sheet = defaultdict(list)
    for sheet in sorted(set(old) | set(new)):
        old_cells = old.get(sheet, {})
        new_cells = new.get(sheet, {})
        all_refs = sorted(set(old_cells) | set(new_cells))
        for ref in all_refs:
            old_val = old_cells.get(ref, "")
            new_val = new_cells.get(ref, "")
            if old_val != new_val:
                per_sheet[sheet].append({"cell": ref, "old": old_val, "new": new_val})
    total = sum(len(v) for v in per_sheet.values())
    return {"total_changes": total, "per_sheet": dict(per_sheet)}


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {}
    with open(state_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)


def pick_new_revisions(revisions: list[dict], last_revision_id: str | None) -> list[dict]:
    if not revisions:
        return []
    if not last_revision_id:
        return revisions
    found = False
    out = []
    for rev in revisions:
        if found:
            out.append(rev)
        elif rev.get("id") == last_revision_id:
            found = True
    return out if found else revisions


def iso_to_pt(iso_str: str | None) -> str:
    if not iso_str:
        return "hora desconhecida"
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00")).astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def shorten(value: str, limit: int = 48) -> str:
    value = (value or "").replace("\n", " ").strip()
    if value == "":
        return "∅"
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def build_summary(diff: dict, max_examples: int = 8) -> dict:
    examples = []
    sheet_counts = []
    for sheet, changes in sorted(diff["per_sheet"].items(), key=lambda kv: (-len(kv[1]), kv[0])):
        sheet_counts.append({"sheet": sheet, "count": len(changes)})
        for change in changes:
            if len(examples) >= max_examples:
                break
            examples.append(
                {
                    "sheet": sheet,
                    "cell": change["cell"],
                    "old": shorten(change["old"]),
                    "new": shorten(change["new"]),
                }
            )
        if len(examples) >= max_examples:
            break
    return {
        "total_changes": diff["total_changes"],
        "sheet_counts": sheet_counts,
        "examples": examples,
    }


def format_message(fmt: str, revision: dict, summary: dict) -> str:
    actor = revision.get("lastModifyingUser", {})
    actor_name = actor.get("displayName") or actor.get("emailAddress") or "Alguém"
    actor_email = actor.get("emailAddress") or "email desconhecido"
    when = iso_to_pt(revision.get("modifiedTime"))
    total = summary["total_changes"]
    top_sheets = ", ".join(f"{x['sheet']}: {x['count']}" for x in summary["sheet_counts"][:4]) or "sem detalhe"
    if fmt == "telegram":
        base = f"⚠️ Sheet Pushnews editada por {actor_name} ({actor_email}). {total} célula(s) mudadas."
        if summary["examples"]:
            ex = summary["examples"][0]
            base += f" Ex: {ex['sheet']}!{ex['cell']} {ex['old']} → {ex['new']}"
        return base
    lines = [
        f"⚠️ **Sheet original da Pushnews alterada por outra pessoa**",
        "",
        f"- **Editor:** {actor_name} (`{actor_email}`)",
        f"- **Quando:** {when}",
        f"- **Mudanças detetadas:** {total} célula(s)",
        f"- **Sheets mais mexidas:** {top_sheets}",
        f"- **Link:** <{FILE_URL}>",
    ]
    if summary["examples"]:
        lines.append("")
        lines.append("**Exemplos do que mudou**")
        for ex in summary["examples"]:
            lines.append(f"- `{ex['sheet']}!{ex['cell']}`: `{ex['old']}` → `{ex['new']}`")
    else:
        lines.append("")
        lines.append("Não consegui extrair diff legível desta alteração, mas a revisão mudou.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["discord", "telegram", "json"], default="json")
    parser.add_argument("--state-dir", default=str(STATE_DIR_DEFAULT))
    args = parser.parse_args()

    state_dir = Path(args.state_dir)
    state_path = state_dir / "state.json"
    snapshot_path = state_dir / "latest.xlsx"
    tmp_snapshot = state_dir / "current.xlsx"
    state_dir.mkdir(parents=True, exist_ok=True)

    revisions = get_revisions()
    if not revisions:
        print(json.dumps({"status": "error", "message": "No revisions found"}))
        return 1

    latest_revision = revisions[-1]
    state = load_state(state_path)
    last_revision_id = state.get("last_revision_id")
    new_revisions = pick_new_revisions(revisions, last_revision_id)

    if not last_revision_id:
        export_snapshot(snapshot_path)
        save_state(
            state_path,
            {
                "last_revision_id": latest_revision.get("id"),
                "last_modified_time": latest_revision.get("modifiedTime"),
                "initialized_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        payload = {"status": "initialized", "last_revision_id": latest_revision.get("id")}
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    if not new_revisions:
        print(json.dumps({"status": "no_change"}, ensure_ascii=False))
        return 0

    foreign_revisions = [
        rev
        for rev in new_revisions
        if (rev.get("lastModifyingUser") or {}).get("emailAddress", "").lower() != OWNER_EMAIL.lower()
    ]

    export_snapshot(tmp_snapshot)
    diff = diff_workbooks(snapshot_path, tmp_snapshot)
    summary = build_summary(diff)
    shutil.move(tmp_snapshot, snapshot_path)
    save_state(
        state_path,
        {
            "last_revision_id": latest_revision.get("id"),
            "last_modified_time": latest_revision.get("modifiedTime"),
            "last_actor": (latest_revision.get("lastModifyingUser") or {}).get("emailAddress"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    if not foreign_revisions:
        print(json.dumps({"status": "owner_only_change"}, ensure_ascii=False))
        return 0

    target_revision = foreign_revisions[-1]
    payload = {
        "status": "alert",
        "actor": target_revision.get("lastModifyingUser"),
        "modifiedTime": target_revision.get("modifiedTime"),
        "latestRevisionId": latest_revision.get("id"),
        "summary": summary,
        "message": format_message(args.format, target_revision, summary),
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["message"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
