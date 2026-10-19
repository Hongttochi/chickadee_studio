"""Validate the imported research offline. Never fetch URLs or interpret HTML."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research/ad-evidence/2026-10-19"
TECHNIQUES = {"HOMOGLYPH", "JAMO", "TRANSPARENT", "OFFSCREEN"}


def validate(folder=DATA):
    folder = Path(folder).resolve()
    manifest = json.loads((folder / "import-manifest.json").read_text(encoding="utf-8"))
    errors, records, ids = [], [], set()
    for item in manifest["files"]:
        path = (ROOT / item["path"]).resolve()
        if not path.is_relative_to(folder):
            raise ValueError("Manifest path leaves research directory")
        raw = path.read_bytes()
        if len(raw) != item["bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
            errors.append(f"Imported bytes changed: {path.name}")
    for name, label in (("samples.jsonl", "ad_suspected"), ("negatives.jsonl", "normal")):
        path = folder / name
        if path.stat().st_size > 1_000_000:
            raise ValueError("Research file exceeds 1 MB")
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            required = {"id", "sample_origin", "observation_status", "source_url", "evidence_text",
                        "label", "techniques", "limitations", "source_group"}
            missing = required - record.keys()
            if missing:
                raise ValueError(f"Missing fields: {missing}")
            key = record["id"]
            if key in ids:
                errors.append(f"Duplicate id: {key}")
            ids.add(key)
            if record["label"] != label or record["sample_origin"] not in ("observed", "reported"):
                errors.append(f"Invalid label/origin: {key}")
            if record["observation_status"] not in ("dom_verified", "visible_only", "reported_only"):
                errors.append(f"Invalid observation status: {key}")
            if (record["sample_origin"] == "reported") != (record["observation_status"] == "reported_only"):
                errors.append(f"Reported/direct conflation: {key}")
            if not isinstance(record["evidence_text"], str) or not record["evidence_text"].strip():
                errors.append(f"Missing evidence text: {key}")
            if not isinstance(record["techniques"], list) or not set(record["techniques"]) <= TECHNIQUES:
                errors.append(f"Invalid techniques: {key}")
            if not isinstance(record["limitations"], list) or not record["limitations"]:
                errors.append(f"Missing limitations: {key}")
            # This import contains NO measured CSS/geometry. Static declarations
            # and labels must never silently become rendered measurements.
            if any(record.get(k) is not None for k in ("computed_style", "bounding_box", "viewport")):
                errors.append(f"Unexpected rendered measurement: {key}")
            parsed = urlsplit(record["source_url"])
            if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username:
                errors.append(f"Invalid source URL: {key}")
            records.append(record)

    summary = {
        "total_records": len(records),
        "origin_counts": dict(Counter(r["sample_origin"] for r in records)),
        "label_counts": dict(Counter(r["label"] for r in records)),
        "status_counts": dict(Counter(r["observation_status"] for r in records)),
        "direct_ad_techniques": dict(Counter(t for r in records if r["sample_origin"] == "observed" and r["label"] == "ad_suspected" for t in r["techniques"])),
        "reported_ad_techniques": dict(Counter(t for r in records if r["sample_origin"] == "reported" and r["label"] == "ad_suspected" for t in r["techniques"])),
    }
    supplied = json.loads((folder / "validation-summary.json").read_text(encoding="utf-8"))
    for field, key in (("origin_counts", "origin"), ("label_counts", "label"), ("status_counts", "status"),
                       ("direct_ad_techniques", "technique"), ("reported_ad_techniques", "technique")):
        if summary[field] != {r[key]: r["count"] for r in supplied[field]}:
            errors.append(f"Supplied summary mismatch: {field}")
    if summary["total_records"] != supplied["total_records"]:
        errors.append("Supplied total mismatch")
    if errors:
        raise ValueError("\n".join(errors))
    return {**summary, "original_files_sha256_verified": len(manifest["files"]),
            "validation_scope": "Offline integrity and metadata only; no detector accuracy claim"}


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=True, indent=2))
