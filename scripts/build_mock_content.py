"""Build the website handoff JSON offline from immutable research and curation."""
import argparse
import html
import json
from pathlib import Path
import unicodedata

from scripts.validate_research import DATA, ROOT, validate

OUTPUT = ROOT / "examples/mock-site-content.json"
SMALL_BOX = {"position": "absolute", "left": "-9999px", "top": "-9999px",
             "width": "1px", "height": "1px", "overflow": "hidden"}
GROUPS = {
    "mixed_hangul_latin": ["A008", "A009", "A016", "A023"],
    "domain_visual_substitution": ["A010", "A011", "A042"],
    "soft_hyphen_separate_pattern": ["A028", "A043"],
    "static_css_hiding": ["A012", "A013", "A015", "A020", "A031"],
    "article_text_insertion": ["A034", "A035"],
    "adult_text_only": ["A021", "A026", "A027", "A040"],
    "casino_service_or_infrastructure": ["A008", "A011", "A025", "A036", "A041", "A046"],
    "promotion_with_prevention_language": ["A007", "A024", "A027", "A045"],
    "same_url_distinct_body_comment": ["A039", "A040"],
    "technique_review_only": ["A022", "A025"],
    "white_text_unknown_background": ["A031", "A044"],
}


def _records(folder):
    return [json.loads(line) for name in ("samples.jsonl", "negatives.jsonl")
            for line in (folder / name).read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _unicode_annotations(blocks):
    annotations = []
    for block_index, text in enumerate(blocks):
        for index, char in enumerate(text):
            point = ord(char)
            if (unicodedata.category(char) == "Cf" or 0x1100 <= point <= 0x11FF or
                    0x3130 <= point <= 0x318F or 0x1D400 <= point <= 0x1D7FF or
                    0xFF00 <= point <= 0xFFEF or 0x0370 <= point <= 0x052F):
                annotations.append({"block_index": block_index, "index": index, "char": char,
                                    "codepoint": f"U+{point:04X}", "name": unicodedata.name(char, "UNKNOWN")})
    return annotations


def build(folder=DATA):
    folder = Path(folder)
    checked = validate(folder)
    records = _records(folder)
    by_id = {r["id"]: r for r in records}
    assert all(set(ids) <= by_id.keys() for ids in GROUPS.values())
    curation = json.loads((folder / "curation.json").read_text(encoding="utf-8"))
    overrides = curation["technique_overrides"]
    placements = []
    for r in records:
        key = r["id"]
        normal = r["label"] == "normal"
        override = overrides.get(key)
        codes = [] if normal else override["conservative_techniques"] if override else r["techniques"]
        item = {
            "id": "CASE_" + key, "source_ids": [key], "content_label": r["label"],
            "content_origin": r["sample_origin"], "observation_status": r["observation_status"],
            "layout_origin": "reconstructed_mock_layout", "context_is_excerpt": True,
            "placement_ko": "모의 사이트 정상 콘텐츠" if normal else "모의 게시판 본문",
            "source_techniques": r["techniques"], "techniques_to_reproduce": codes,
            "additional_patterns": r.get("additional_patterns", []),
            "additional_features": r.get("additional_features", []),
            "detector_result": "not_measured", "ready_to_place": key not in ("R003", "R005"),
            "render_method": "textContent",
            "text_blocks": [r["evidence_text"], *r.get("evidence_fragments", [])],
            "groups": [group for group, ids in GROUPS.items() if key in ids],
        }
        if normal:
            item["expected_detector_techniques"] = []
        if override:
            item["technique_review"] = override
        if key in curation["case_notes"]:
            item["notes_ko"] = curation["case_notes"][key]
        if key in ("R003", "R005"):
            item["notes_ko"] = "문헌 설명 또는 도메인 접미부 발췌만 있어 완전한 원 광고 문구로 사용하지 않는다. 자료 보기용 텍스트로만 취급한다."
        if key in ("N002", "N007"):
            item["ancestor_style"] = {"display": "none"}
            item["notes_ko"] = "정상 숨김 UI의 대조군이다. CSS 비표시가 있어도 광고로 분류하지 않아야 한다."
        if key in ("A009", "A040"):
            item["placement_ko"] = "모의 게시글 아래 별도 댓글"
        if key in ("A012", "A013", "A020"):
            item["placement_ko"] = "모의 교육·학술 사이트 footer"
            item["ancestor_style"] = {"display": "none"} if key != "A020" else dict(SMALL_BOX)
        if key == "A013":
            item["text_blocks"] = [r["evidence_text"]]
        if key == "A015":
            item["placement_ko"] = "모의 상품 상세 페이지 하단"
            item["element_style"] = r["declared_style"]
        if key == "A031":
            item["element_style"] = {"font-size": "1px"}
            item["style_subset_note_ko"] = "원 선언 중 font-size만 재구성한다. 흰 글자는 미측정 배경에서 투명해진다고 단정할 수 있어 재현 스타일에 넣지 않았다. 전체 원 선언은 real_cases의 dom_excerpt에 보존한다."
        if key in ("R004", "R006"):
            item["element_style"] = r["reported_style"]
        if key == "R007":
            item["ordered_style_rules"] = r["reported_style_rules"]
            item["notes_ko"] = "문헌 보고 재구성. ads-gold 클래스와 CSS 선언 순서를 유지한다. 최종 height:0px/overflow:hidden이 앞 선언을 덮어쓴다."
        if key == "A014":
            item["text_blocks"] = [html.unescape(r["dom_excerpt"])]
            item["notes_ko"] = "HTML 엔티티를 풀어 일반 텍스트로만 배치한다. innerHTML로 넣거나 실제 a 요소·숨김 스타일을 만들면 원 사례와 달라진다."
        placements.append(item)
    placements.append({
        "id": "CASE_A013_NEGATIVE_BOX", "source_ids": ["A013"],
        "content_label": "ad_suspected", "content_origin": "observed",
        "observation_status": "dom_verified", "layout_origin": "reconstructed_mock_layout",
        "placement_ko": "같은 학술지 footer의 별도 링크", "text_blocks": ["slot777"],
        "render_method": "textContent", "source_techniques": ["OFFSCREEN"],
        "techniques_to_reproduce": ["OFFSCREEN"], "ancestor_style": dict(SMALL_BOX),
        "detector_result": "not_measured", "ready_to_place": True,
        "notes_ko": "A013 추가 DOM 발췌에 있는 실제 문자열·스타일. 독립 원본 사례로 추가 집계하지 않는다."
    })
    for item in placements:
        item["unicode_annotations"] = _unicode_annotations(item["text_blocks"])
        assert set(item["source_ids"]) <= by_id.keys()
        if item["id"] != "CASE_A014":
            originals = [text for key in item["source_ids"] for text in
                         [by_id[key]["evidence_text"], *by_id[key].get("evidence_fragments", [])]]
            assert all(text in originals for text in item["text_blocks"]), item["id"]
    assert not set(curation["excluded_ids"]) & by_id.keys()
    return {
        "spec_version": "2.0", "dataset_version": "v4-curated-1",
        "title_ko": "모의 웹 제작용 실제 조사 원문·배치·CSS 근거",
        "content_ko": "real_cases는 원본 적격 78건을 변경 없이 담는다. placement_examples는 원문 발췌를 배치하는 재구성 명세이며 독립 사례 수가 아니다.",
        "source_directory": folder.relative_to(ROOT).as_posix(),
        "counts": {"real_cases": len(records), "observed": checked["origin_counts"]["observed"],
                   "observed_ad_suspected": checked["v4_counts"]["observed_ad_suspected"],
                   "reported": checked["v4_counts"]["reported"], "ad_suspected": checked["v4_counts"]["samples"],
                   "normal": checked["v4_counts"]["negatives"],
                   "added_records": checked["added_records"], "unchanged_legacy_records": checked["unchanged_legacy_records"],
                   "placement_examples": len(placements), "excluded_ids": curation["excluded_ids"],
                   "observed_ad_source_groups": checked["v4_counts"]["unique_observed_source_groups"],
                   "observed_ad_source_urls": checked["v4_counts"]["unique_observed_source_urls"],
                   "source_labeled_technique_cases": checked["source_labeled_technique_cases"],
                   "conservative_technique_cases": checked["conservative_technique_cases"],
                   "conservative_ad_techniques": checked["conservative_ad_techniques"],
                   "direct_transparent_cases": 0, "computed_css_verified": 0},
        "render_contract": {
            "default_text_insertion": "textContent",
            "source_urls": "출처 메타데이터로만 보관한다. 출처 URL·광고 목적지·이미지·스크립트를 요청하지 않는다.",
            "dom_excerpt": "근거 문자열이다. 수집한 HTML을 실행하거나 통째로 렌더링하지 않는다.",
            "style_application": "element_style은 텍스트 요소, ancestor_style은 감싸는 조상에 적용한다. ordered_style_rules는 자체 작성 CSS에 순서대로 반영한다.",
            "text_preservation": "원문 Unicode·공백을 유지한다. 분리된 발췌를 원래 연속 본문으로 표시하지 않는다. textContent 블록 사이 임의 문구·가입 링크를 추가하지 않는다.",
            "unknown_content": "삭제된 도메인·연락처·제목·누락 본문과 미측정 배경·스타일은 복원하지 않는다.",
            "source_measurements": "dom_verified는 정적 HTML/문자 확인 수준이다. computed_style·bounding_box·viewport null은 미측정이며 정상이라는 뜻이 아니다.",
            "reported_cases": "reported는 원 피해 페이지를 직접 관찰한 사례와 구분한다.",
            "expected_results": "source_techniques는 원본 라벨, techniques_to_reproduce는 보수적 제작 대상이다. 탐지 성공·실제 계산 CSS·불법성의 확정 결과가 아니다.",
            "additional_patterns": "soft hyphen·구두점 삽입 등은 별도 패턴이며 필수 4종 양성으로 강제 변환하지 않는다.",
            "unicode_annotations": "각 text_blocks의 0부터 시작하는 문자 위치·코드 포인트다. 원문을 바꾸지 않는다. 키릴·그리스·전각·자모·서식 문자 존재만으로 위장 의도를 판정하지 않는다.",
            "normal_controls": "정상 숨김 UI·교재·지명·상품·기사 인용은 광고 문구와 구별한다.",
            "exclusions": "A019는 제외 부록에만 있고 이 제작 파일에는 없다. 429·접근 실패를 광고 부재나 정상으로 바꾸지 않는다.",
            "runtime_boundary": "모의 사이트에는 실제 취약점·외부 매체·외부 스크립트·실제 자격증명이 필요 없다. 자체 자원만 사용한다."
        },
        "placement_groups": GROUPS, "curation": curation,
        "placement_examples": placements, "real_cases": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check committed output without modifying files")
    args = parser.parse_args()
    payload = (json.dumps(build(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != payload:
            raise SystemExit("Mock content JSON is out of date; run python -m scripts.build_mock_content")
        print("Mock content is current: 78 original records, 35 additions, 79 placements, no excluded A019.")
    else:
        OUTPUT.write_bytes(payload)
        print("Updated " + OUTPUT.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
