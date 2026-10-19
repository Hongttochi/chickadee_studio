"""Validate the imported research offline. Never fetch URLs or interpret HTML."""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
LEGACY_DATA = ROOT / "research/ad-evidence/2026-10-19"
DATA = ROOT / "research/ad-evidence/2026-10-19-v4"
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
    if (folder / "validation.json").exists():
        summary.update(_validate_v4(folder, records, manifest, errors))
        if errors:
            raise ValueError("\n".join(errors))
        return {**summary, "original_files_sha256_verified": len(manifest["files"]),
                "validation_scope": "Offline integrity, metadata, curation and delta only; no detector accuracy claim"}
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


def _rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _validate_v4(folder, records, manifest, errors):
    supplied = json.loads((folder / "validation.json").read_text(encoding="utf-8"))
    ads = [r for r in records if r["sample_origin"] == "observed" and r["label"] == "ad_suspected"]
    actual = {
        "samples": sum(r["label"] == "ad_suspected" for r in records),
        "observed_ad_suspected": len(ads), "reported": sum(r["sample_origin"] == "reported" for r in records),
        "negatives": sum(r["label"] == "normal" for r in records),
        "unique_ids": len({r["id"] for r in records}),
        "unique_observed_source_groups": len({r["source_group"] for r in ads}),
        "unique_observed_source_urls": len({r["source_url"] for r in ads}),
        "dom_verified_ad": sum(r["observation_status"] == "dom_verified" for r in ads),
        "visible_only_ad": sum(r["observation_status"] == "visible_only" for r in ads),
        "computed_css_verified": sum(r.get("computed_style") is not None for r in records),
        "technique_ids": {t: sorted(r["id"] for r in ads if t in r["techniques"]) for t in sorted(TECHNIQUES)},
        "excluded_ids": sorted(r["id"] for r in _rows(folder / "excluded-records.jsonl")),
    }
    for key, value in actual.items():
        if value != supplied[key]:
            errors.append(f"Supplied v4 summary mismatch: {key}")
    ids = {r["id"] for r in records}
    if ids & set(actual["excluded_ids"]):
        errors.append("Excluded records leaked into admissible dataset")
    excluded = _rows(folder / "excluded-records.jsonl")
    if any(not r.get("exclusion_reason") for r in excluded):
        errors.append("Missing exclusion reason")
    previous = (ROOT / manifest["previous_dataset"]).resolve()
    if not previous.is_relative_to(ROOT / "research/ad-evidence"):
        raise ValueError("Previous dataset path leaves research directory")
    old = {r["id"]: r for name in ("samples.jsonl", "negatives.jsonl") for r in _rows(previous / name)}
    current = {r["id"]: r for r in records}
    if any(current.get(key) != row for key, row in old.items()):
        errors.append("Legacy records changed or removed without revision metadata")
    added = [r for r in records if r["id"] not in old]
    new_rows = _rows(folder / "new-observed.jsonl")
    if len(new_rows) != len(added) or {r["id"]: r for r in new_rows} != {r["id"]: r for r in added}:
        errors.append("new-observed does not match the actual delta")
    curation = json.loads((folder / "curation.json").read_text(encoding="utf-8"))
    overrides = curation["technique_overrides"]
    for key, value in overrides.items():
        if key not in current or not set(value["conservative_techniques"]) <= set(current[key]["techniques"]) or not value.get("reason_ko"):
            errors.append(f"Invalid curation override: {key}")
    if sorted(curation["excluded_ids"]) != actual["excluded_ids"] or not set(curation["case_notes"]) <= ids:
        errors.append("Curation references unknown or mismatched IDs")
    conservative = {r["id"]: overrides.get(r["id"], {}).get("conservative_techniques", r["techniques"]) for r in ads}
    for attachment in manifest.get("standalone_attachments", []):
        member = next((f for f in manifest["files"] if Path(f["path"]).name == attachment["name"]), None)
        if member is None or member["sha256"] != attachment["sha256"]:
            errors.append("Standalone attachment/archive mismatch")
    return {"v4_counts": actual, "unchanged_legacy_records": len(old), "added_records": len(added),
            "source_labeled_technique_cases": sum(bool(r["techniques"]) for r in ads),
            "conservative_technique_cases": sum(bool(t) for t in conservative.values()),
            "conservative_ad_techniques": dict(Counter(t for ts in conservative.values() for t in ts)),
            "technique_review_ids": sorted(overrides)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATA)
    print(json.dumps(validate(parser.parse_args().dataset), ensure_ascii=True, indent=2))
