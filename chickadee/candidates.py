"""Review candidates without asserting illegality or inventing an evasion code."""
import re
from functools import lru_cache

from .detection import DEFAULT_RULES, analyze, skeleton, is_editorial_context, text_ranges, merge_analyses

CATEGORY_LABELS = {"GAMBLING": "도박 홍보 의심", "ADULT": "성인 콘텐츠 홍보 의심",
                   "LOAN": "대출 모집 의심", "INVESTMENT": "투자 모집 의심", "COMMERCIAL": "구매·추천 유도",
                   "AI_CONTEXT": "AI 광고 문맥"}


@lru_cache(maxsize=512)
def analyze_candidate(text, rules=DEFAULT_RULES, breaks=()):
    if breaks:
        grouped = {}
        for start, end in text_ranges(text, breaks):
            for hit in analyze_candidate(text[start:end], rules):
                category = hit['category']
                if category not in grouped:
                    grouped[category] = {**hit, 'matched_keywords':[], 'reasons':[], '_analyses':[]}
                combined = grouped[category]
                combined['matched_keywords'].extend(k for k in hit['matched_keywords'] if k not in combined['matched_keywords'])
                combined['reasons'].extend(r for r in hit['reasons'] if r not in combined['reasons'])
                if 'analysis' in hit:
                    combined['_analyses'].append((start, hit['analysis']))
        for hit in grouped.values():
            parts = hit.pop('_analyses')
            if parts:
                hit['analysis'] = merge_analyses(parts, rules)
        return list(grouped.values())
    if is_editorial_context(text):
        return []
    result = []
    base = analyze(text, rules)
    if base["is_advertisement"]:
        keywords = list(dict.fromkeys(m["keyword"] for m in base["matches"]))
        adult = any(k in {"야동", "porn", "성인방송", "성인사이트", "성인물"} for k in keywords)
        result.append({"category": "ADULT" if adult else "GAMBLING", "matched_keywords": keywords,
                       "reasons": ["광고 주제어와 근접한 권유 문맥"], "analysis": base})
    # Other domains remain review candidates, never mandatory technique findings.
    compact = skeleton(text)
    linked = bool(re.search(r"https?://[^\s<>]+", text, re.I))
    def contains(term):
        return skeleton(term) in compact
    for category, topics, signals in (
        ("LOAN", ("대출", "대부"), ("상담 신청", "즉시 입금", "신용 확인 없이", "당일 대출")),
        ("INVESTMENT", ("투자",), ("수익 보장", "원금 보장", "고수익", "투자 모집")),
        ("COMMERCIAL", ("상품 주문", "추천 수당"), ("특별 할인", "추천 수당", "구매 혜택")),
    ):
        hits = [t for t in topics if contains(t)]
        selling = [t for t in signals if contains(t)]
        if linked and hits and selling:
            result.append({"category": category, "matched_keywords": hits,
                           "reasons": ["외부 주소가 포함된 모집·구매 권유", *selling]})
    return result


def classify_candidates(elements, rules=None):
    """Prefer leaf evidence; group title/body within the same article or comment."""
    rules = rules or DEFAULT_RULES
    by_id = {e["node_id"]: e for e in elements}
    hits, ancestor_hits = [], set()
    for element in elements:
        for analysis in analyze_candidate(element["text"], rules, tuple(element.get('text_breaks', []))):
            hit = {**element, **analysis}
            hits.append(hit)
            parent = hit["parent_id"]
            while parent is not None and parent in by_id:
                ancestor_hits.add((parent, hit["category"]))
                parent = by_id[parent]["parent_id"]
    grouped = {}
    for hit in hits:
        if (hit["node_id"], hit["category"]) in ancestor_hits:
            continue
        key = hit.get("content_scope") or hit["location"], hit["category"]
        previous = grouped.get(key)
        if previous is None or len(hit["text"]) > len(previous["text"]):
            grouped[key] = hit
    return list(grouped.values())
