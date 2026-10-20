"""Versioned, fixed-column CSV. Raw evidence remains untouched in JSON."""
import csv
import io
import json
import os
from pathlib import Path
import tempfile

from .detection import LABELS
from .candidates import CATEGORY_LABELS

CSV_COLUMNS = ("schema_version", "record_kind", "id", "url", "category", "technique", "technique_name",
               "is_violation", "review_required", "evidence_text", "location", "matched_keywords",
               "style_reasons", "frame_depth", "observed_at", "rules_version", "tool_version")


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    elif isinstance(value, bool):
        value = "true" if value else "false"
    value = str(value)
    # Untrusted text must not become an Excel/LibreOffice formula on opening.
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def csv_bytes(result, report):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\r\n")
    writer.writeheader()
    entries = [("technique_finding", f) for f in result["findings"]]
    entries.extend(("ad_candidate", c) for c in report.get("ad_candidates", []))
    for kind, entry in entries:
        detail = report.get("evidence_details", {}).get(entry["id"], {}) if kind == "technique_finding" else entry
        analysis = detail.get("analysis", {})
        code = entry.get("technique", "")
        row = {
            "schema_version": "1.0", "record_kind": kind, "id": entry["id"], "url": entry["url"],
            "category": entry.get("category", ""), "technique": code,
            "technique_name": LABELS.get(code, CATEGORY_LABELS.get(entry.get("category"), "")),
            "is_violation": entry.get("is_violation"), "review_required": True,
            "evidence_text": entry["evidence_text"], "location": entry["location"],
            "matched_keywords": detail.get("matched_keywords", list(dict.fromkeys(m["keyword"] for m in analysis.get("matches", [])))),
            "style_reasons": detail.get("style_reasons", detail.get("reasons", [])),
            "frame_depth": entry["location"].count(" >>> "), "observed_at": detail.get("observed_at", ""),
            "rules_version": report.get("rules_version", ""), "tool_version": result["meta"].get("tool_version", ""),
        }
        writer.writerow({key: _cell(row[key]) for key in CSV_COLUMNS})
    return output.getvalue().encode("utf-8-sig")


def atomic_write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".chickadee-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
