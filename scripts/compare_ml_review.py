"""Offline comparison with supplied predictions; no training, browsing or LLM calls.

The current engine sees evidence_text only. A missing candidate means 'not
flagged', not 'normal'. This is not a rendered four-technique evaluation.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chickadee import __version__
from chickadee.candidates import analyze_candidate

REVIEW = ROOT / 'research/ml-review/2026-10-21'
DATA = ROOT / 'research/ad-evidence/2026-10-19-v4'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def scores(labels, flags):
    if not labels or len(labels) != len(flags):
        raise ValueError('Expected nonempty aligned labels and predictions.')
    tp = sum(y and p for y, p in zip(labels, flags))
    fp = sum(not y and p for y, p in zip(labels, flags))
    fn = sum(y and not p for y, p in zip(labels, flags))
    tn = len(labels) - tp - fp - fn
    return {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
            'precision': tp / (tp + fp) if tp + fp else None,
            'recall': tp / (tp + fn) if tp + fn else None,
            'balanced_accuracy': (tp / (tp + fn) + tn / (tn + fp)) / 2
            if tp + fn and tn + fp else None}


def align(records, predictions):
    direct = [r for r in records if r['sample_origin'] == 'observed']
    by_id = {r['id']: r for r in direct}
    if len(by_id) != len(direct) or len({r['id'] for r in predictions}) != len(predictions):
        raise ValueError('Duplicate sample ID.')
    if set(by_id) != {r['id'] for r in predictions}:
        raise ValueError('Direct observations and supplied predictions do not align.')
    for prediction in predictions:
        row = by_id[prediction['id']]
        if row['label'] not in ('normal', 'ad_suspected'):
            raise ValueError('Unsupported label.')
        if any(row[k] != prediction[k] for k in ('label', 'evidence_text')):
            raise ValueError('Supplied prediction text or label differs from source.')
    return [by_id[p['id']] for p in predictions]


def compare(review=REVIEW, data=DATA):
    manifest = json.loads((review / 'import-manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['files'].items():
        path = (review / name).resolve()
        if not path.is_relative_to(review.resolve()) or digest(path) != expected:
            raise ValueError('Review integrity mismatch: ' + name)
    original = review / 'originals'
    supplied = json.loads((original / 'metrics.json').read_text(encoding='utf-8'))
    for name in ('samples.jsonl', 'negatives.jsonl'):
        if digest(data / name) != supplied['input_sha256'][name]:
            raise ValueError('Source data hash differs from supplied review: ' + name)
    records = rows(data / 'samples.jsonl') + rows(data / 'negatives.jsonl')
    predictions = rows(original / 'predictions.jsonl')
    direct = align(records, predictions)
    labels = [r['label'] == 'ad_suspected' for r in direct]
    reference = {}
    flags = {}
    for model in supplied['oof_metrics']:
        values = [p['predictions'][model] for p in predictions]
        if any(v not in ('normal', 'ad_suspected') for v in values):
            raise ValueError('Unsupported prediction label.')
        flags[model] = [v == 'ad_suspected' for v in values]
        reference[model] = scores(labels, flags[model])
        s = reference[model]
        if [[s['tn'], s['fp']], [s['fn'], s['tp']]] != supplied['oof_metrics'][model]['confusion_matrix']:
            raise ValueError('Supplied metrics do not match per-sample predictions.')
    current_hits = [analyze_candidate(r['evidence_text']) for r in direct]
    current = [bool(hits) for hits in current_hits]
    rf = flags['rf_char_tfidf']
    output_rows = [{'id': r['id'], 'label': r['label'],
                    'current_candidate': bool(hits), 'categories': [h['category'] for h in hits],
                    'supplied_rf_candidate': b,
                    'agreement': bool(hits) == b,
                    'needs_more_context': not bool(hits) and r['label'] == 'ad_suspected'}
                   for r, hits, b in zip(direct, current_hits, rf)]
    return {
        'scope': 'Selected-fragment candidate coverage only; NOT live-site, mandatory-technique, phishing or legal accuracy.',
        'engine_version': __version__,
        'engine_sha256': {name: digest(ROOT / 'chickadee' / name)
                          for name in ('candidates.py', 'detection.py', 'rules.json')},
        'review_archive_sha256': manifest['archive_sha256'],
        'input_sha256': supplied['input_sha256'],
        'n': len(direct), 'labels': dict(Counter(r['label'] for r in direct)),
        'excluded_indirect': sum(r['sample_origin'] == 'reported' for r in records),
        'input': 'evidence_text verbatim; no source URL, HTML, CSS, label or annotation supplied to current engine',
        'current_rules': scores(labels, current),
        'supplied_prototypes_recounted': reference,
        'hypothetical_rule_or_supplied_rf': scores(labels, [a or b for a, b in zip(current, rf)]),
        'limitations': [
            'Reference RF predictions were recounted, not retrained or independently reproduced.',
            'Current fixed rules have seen research-derived regressions; this is not an untouched evaluation set.',
            'RF used collector-marker removal; current rules received verbatim evidence_text. Inputs differ in preprocessing.',
            'Not flagged means unresolved, not a verified normal result; no missing CSS is fabricated.',
            'Union combines fixed rules and supplied out-of-fold RF only as a diagnostic; not a deployed hybrid or performance promise.',
            'Only already selected fragments tested. Scope retrieval, DOM/frame location and unseen campaigns not tested.',
        ],
        'cases': output_rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Optional JSON diagnostic output; no scan files are changed.')
    args = parser.parse_args()
    result = compare()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('cases', 'limitations')}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
